"""Atomic hot/cold maintenance and physical accounting for SQLiteSourceState."""
from __future__ import annotations

from pathlib import Path
from .maintenance import SourceStateRetention, SourceStateMaintenance, record_authority


class SQLiteRetention:
    def _initialize_retention(self):
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS cold_records AS SELECT * FROM records WHERE 0;
            CREATE UNIQUE INDEX IF NOT EXISTS cold_records_key ON cold_records(stream,record_id);
            CREATE INDEX IF NOT EXISTS cold_records_page ON cold_records(stream,source_id,sequence,record_id);
            CREATE INDEX IF NOT EXISTS cold_records_value ON cold_records(stream,represented_value_id);
            CREATE INDEX IF NOT EXISTS cold_records_accepted ON cold_records(stream,accepted_id);
            CREATE TABLE IF NOT EXISTS cold_authority AS SELECT * FROM authority WHERE 0;
            CREATE UNIQUE INDEX IF NOT EXISTS cold_authority_key ON cold_authority(stream,kind,identity);
            CREATE INDEX IF NOT EXISTS cold_authority_lookup ON cold_authority(kind,identity);
            CREATE TABLE IF NOT EXISTS cold_retention_links AS SELECT * FROM retention_links WHERE 0;
            CREATE UNIQUE INDEX IF NOT EXISTS cold_links_key ON cold_retention_links(stream,accepted_id);
            CREATE VIEW IF NOT EXISTS all_records AS SELECT * FROM records UNION ALL SELECT * FROM cold_records;
            CREATE VIEW IF NOT EXISTS all_authority AS SELECT * FROM authority UNION ALL SELECT * FROM cold_authority;
            CREATE VIEW IF NOT EXISTS all_retention_links AS SELECT * FROM retention_links UNION ALL SELECT * FROM cold_retention_links;
            CREATE TABLE IF NOT EXISTS cold_usage(singleton INTEGER PRIMARY KEY CHECK(singleton=1), count INTEGER NOT NULL, bytes INTEGER NOT NULL);
            INSERT OR IGNORE INTO cold_usage VALUES(1,0,0);
            CREATE TABLE IF NOT EXISTS history_horizons(stream TEXT PRIMARY KEY, retired_through INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS authority_refs(stream TEXT NOT NULL, record_id TEXT NOT NULL,
                kind TEXT NOT NULL, identity TEXT NOT NULL, PRIMARY KEY(stream,record_id,kind,identity));
            CREATE INDEX IF NOT EXISTS authority_refs_lookup ON authority_refs(stream,kind,identity);
            CREATE TABLE IF NOT EXISTS reference_index(stream TEXT NOT NULL,record_id TEXT NOT NULL,
                PRIMARY KEY(stream,record_id));
        ''')
        if 'sequence' not in {row[1] for row in self._db.execute('PRAGMA table_info(cold_retention_links)')}:
            self._db.execute('ALTER TABLE cold_retention_links ADD COLUMN sequence INTEGER NOT NULL DEFAULT 9223372036854775807')

    def _index_references(self, stream, identity, value):
        self._db.execute('DELETE FROM authority_refs WHERE stream=? AND record_id=?', (stream, identity))
        self._db.executemany('INSERT OR IGNORE INTO authority_refs VALUES(?,?,?,?)',
                             ((stream, identity, kind, key) for kind, key in record_authority(value)))
        self._db.execute('INSERT OR IGNORE INTO reference_index VALUES(?,?)', (stream, identity))

    def rebuild_reference_index(self, *, limit=1000):
        """Resume an exact metadata-only index rebuild for an existing checkpoint."""
        from .sqlite import _decode
        if type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError('source_state.page_invalid')
        with self._lock:
            self._db.execute('BEGIN IMMEDIATE')
            try:
                rows = self._db.execute('''SELECT stream,record_id,payload FROM all_records r
                    WHERE NOT EXISTS(SELECT 1 FROM reference_index i WHERE i.stream=r.stream AND i.record_id=r.record_id)
                    ORDER BY stream,record_id LIMIT ?''', (limit,)).fetchall()
                for stream, identity, payload in rows:
                    self._index_references(stream, identity, _decode(payload))
                self._db.execute('COMMIT')
                return len(rows)
            except BaseException:
                self._db.execute('ROLLBACK')
                raise

    def _history_floor(self, stream):
        row = self._db.execute('SELECT retired_through FROM history_horizons WHERE stream=?', (stream,)).fetchone()
        return row[0] if row else 0

    def _cold_reserve(self, count, size):
        old_count, old_size = self._db.execute('SELECT count,bytes FROM cold_usage WHERE singleton=1').fetchone()
        if old_count + count > self.max_archive_records or old_size + size > self.max_archive_bytes:
            raise ValueError('source_state.archive_capacity_exhausted')
        self._db.execute('UPDATE cold_usage SET count=count+?,bytes=bytes+? WHERE singleton=1', (count, size))

    @staticmethod
    def _row_size(table, row):
        return len(row[2].encode()) if table == 'retention_links' else (
            len(row[1].encode()) + len(row[2].encode()) + 16 if table == 'authority' else len(row[9].encode()))

    def _move_cold(self, table, row):
        key_columns = {'records': ('stream', 'record_id'), 'authority': ('stream', 'kind', 'identity'),
                       'retention_links': ('stream', 'accepted_id')}[table]
        size = self._row_size(table, row)
        self._cold_reserve(1, size)
        self._db.execute('INSERT INTO cold_' + table + ' VALUES(' + ','.join('?' for _ in row) + ')', row)
        self._db.execute('DELETE FROM ' + table + ' WHERE ' + ' AND '.join(key + '=?' for key in key_columns), row[:len(key_columns)])
        self._db.execute('UPDATE usage SET count=count-1,bytes=bytes-? WHERE singleton=1', (size,))

    def _delete_row(self, table, row, cold):
        key_columns = {'records': ('stream', 'record_id'), 'authority': ('stream', 'kind', 'identity'),
                       'retention_links': ('stream', 'accepted_id')}[table]
        self._db.execute('DELETE FROM ' + ('cold_' if cold else '') + table + ' WHERE ' +
                         ' AND '.join(key + '=?' for key in key_columns), row[:len(key_columns)])
        self._db.execute('UPDATE ' + ('cold_usage' if cold else 'usage') +
                         ' SET count=count-1,bytes=bytes-? WHERE singleton=1', (self._row_size(table, row),))

    def maintain(self, *, stream_id, policy):
        """Commit at most ``policy.limit`` pointer retirements/removals/moves.

        Cold tables share the owner's SQLite transaction and remain queryable.
        Their capacity is independent and explicit. Discard retires only evidence
        outside the current projection and records a permanent history horizon.
        """
        if not isinstance(policy, SourceStateRetention):
            raise TypeError('source_state.retention_policy_required')
        with self._lock:
            checkpoint = self.checkpoint(stream_id)
            if checkpoint is None or policy.through > checkpoint.applied_through:
                raise ValueError('source_state.compaction_cursor_invalid')
            self._db.execute('BEGIN IMMEDIATE')
            try:
                result = self._maintain(stream_id, policy)
                self._db.execute('COMMIT')
                return result
            except BaseException:
                self._db.execute('ROLLBACK')
                raise

    def _maintain(self, stream, policy):
        # An effective method/material basis is independently reusable. The
        # host names the accepted outputs whose current designation it retires;
        # chronology alone never makes another requested basis obsolete.
        retired_current = ()
        current_where = None
        current_args = []
        if policy.retire_current_accepted_ids:
            current_where = '''c.stream=? AND r.sequence<=? AND r.record_kind='RetainedOutput'
                AND r.accepted_id IN (''' + ','.join('?' for _ in policy.retire_current_accepted_ids) + ')'
            current_args = [stream, policy.through, *policy.retire_current_accepted_ids]
            if policy.protected_accepted_ids:
                current_where += ' AND r.accepted_id NOT IN (' + ','.join('?' for _ in policy.protected_accepted_ids) + ')'
                current_args.extend(policy.protected_accepted_ids)
            retired_current = self._db.execute('''SELECT c.fold_key,c.record_id
                FROM current_records c JOIN all_records r ON r.stream=c.stream AND r.record_id=c.record_id
                WHERE ''' + current_where + ' ORDER BY r.sequence,r.record_id,c.fold_key LIMIT ?',
                (*current_args, policy.limit)).fetchall()
            for fold_key, identity in retired_current:
                self._db.execute('DELETE FROM current_records WHERE stream=? AND fold_key=? AND record_id=?',
                                 (stream, fold_key, identity))
        remaining = policy.limit - len(retired_current)
        discard = policy.disposition == 'discard'
        relation = 'all_records' if discard else 'records'
        where = '''r.stream=? AND r.sequence<=? AND NOT EXISTS(SELECT 1 FROM current_records c
            WHERE c.stream=r.stream AND c.record_id=r.record_id)'''
        args = [stream, policy.through]
        if policy.protected_accepted_ids:
            where += ' AND (r.accepted_id IS NULL OR r.accepted_id NOT IN (' + ','.join('?' for _ in policy.protected_accepted_ids) + '))'
            args.extend(policy.protected_accepted_ids)
        if discard:
            # A current semantic value can depend on an older encoded carrier.
            where += ''' AND NOT EXISTS(SELECT 1 FROM all_records live JOIN current_records c
                ON c.stream=live.stream AND c.record_id=live.record_id WHERE live.stream=r.stream
                AND r.represented_value_id=live.value_identity)'''
            if not policy.retire_persistent:
                where += ''' AND (r.record_kind='SourceObservation' OR (r.persistent=0
                    AND NOT EXISTS(SELECT 1 FROM all_retention_links l WHERE l.stream=r.stream AND l.accepted_id=r.accepted_id)
                    AND NOT EXISTS(SELECT 1 FROM all_records p LEFT JOIN all_retention_links l
                        ON l.stream=p.stream AND l.accepted_id=p.accepted_id
                        WHERE p.stream=r.stream AND p.represented_value_id=r.value_identity
                        AND (p.persistent=1 OR l.payload IS NOT NULL))))'''
        rows = self._db.execute('SELECT r.* FROM ' + relation + ' r WHERE ' + where +
                                ' ORDER BY sequence,record_id LIMIT ?', (*args, remaining)).fetchall()
        for row in rows:
            if discard:
                cold = self._db.execute('SELECT 1 FROM cold_records WHERE stream=? AND record_id=?', row[:2]).fetchone() is not None
                self._delete_row('records', row, cold)
                self._db.execute('DELETE FROM authority_refs WHERE stream=? AND record_id=?', row[:2])
                self._db.execute('DELETE FROM reference_index WHERE stream=? AND record_id=?', row[:2])
            else:
                self._move_cold('records', row)
        if discard and rows:
            retired = max(row[2] for row in rows)
            self._db.execute('''INSERT INTO history_horizons VALUES(?,?) ON CONFLICT(stream)
                DO UPDATE SET retired_through=max(retired_through,excluded.retired_through)''', (stream, retired))
        remaining -= len(rows)
        link_relation = 'all_retention_links' if discard else 'retention_links'
        retained_relation = 'all_records' if discard else 'records'
        link_where = '''l.stream=? AND l.sequence<=? AND NOT EXISTS(SELECT 1 FROM ''' + retained_relation + ''' r
            WHERE r.stream=l.stream AND r.accepted_id=l.accepted_id)'''
        link_args = [stream, policy.through]
        if policy.protected_accepted_ids:
            link_where += ' AND l.accepted_id NOT IN (' + ','.join('?' for _ in policy.protected_accepted_ids) + ')'
            link_args.extend(policy.protected_accepted_ids)
        links = self._db.execute('SELECT l.* FROM ' + link_relation + ' l WHERE ' + link_where +
                                 ' ORDER BY accepted_id LIMIT ?', (*link_args, remaining)).fetchall()
        for row in links:
            if discard:
                cold = self._db.execute('SELECT 1 FROM cold_retention_links WHERE stream=? AND accepted_id=?', row[:2]).fetchone() is not None
                self._delete_row('retention_links', row, cold)
            else:
                self._move_cold('retention_links', row)
        if discard and links:
            self._db.execute('''INSERT INTO history_horizons VALUES(?,?) ON CONFLICT(stream)
                DO UPDATE SET retired_through=max(retired_through,excluded.retired_through)''',
                (stream, max(row[3] for row in links)))
        remaining -= len(links)
        authority_relation = 'all_authority' if discard else 'authority'
        auth_where, auth_args = 'a.stream=? AND a.sequence<=?', [stream, policy.through]
        if discard:
            # A restored older checkpoint must rebuild its exact reference index
            # before authority can be retired. This fails closed, in bounded work.
            auth_where += ''' AND NOT EXISTS(SELECT 1 FROM authority_refs r WHERE r.stream=a.stream AND r.kind=a.kind AND r.identity=a.identity)
                AND NOT EXISTS(SELECT 1 FROM all_records r WHERE r.stream=a.stream AND NOT EXISTS(
                    SELECT 1 FROM reference_index i WHERE i.stream=r.stream AND i.record_id=r.record_id))'''
            for kind, identity in policy.protected_authority:
                auth_where += ' AND NOT (a.kind=? AND a.identity=?)'
                auth_args.extend((kind, identity))
        authorities = self._db.execute('SELECT a.* FROM ' + authority_relation + ' a WHERE ' + auth_where +
                                       ' ORDER BY sequence,kind,identity LIMIT ?', (*auth_args, remaining)).fetchall()
        for row in authorities:
            if discard:
                cold = self._db.execute('SELECT 1 FROM cold_authority WHERE stream=? AND kind=? AND identity=?', row[:3]).fetchone() is not None
                self._delete_row('authority', row, cold)
            else:
                self._move_cold('authority', row)
        has_more = any((
            self._db.execute('SELECT 1 FROM ' + relation + ' r WHERE ' + where + ' LIMIT 1', args).fetchone(),
            self._db.execute('SELECT 1 FROM ' + link_relation + ' l WHERE ' + link_where + ' LIMIT 1', link_args).fetchone(),
            self._db.execute('SELECT 1 FROM ' + authority_relation + ' a WHERE ' + auth_where + ' LIMIT 1', auth_args).fetchone(),
            self._db.execute('''SELECT 1 FROM current_records c JOIN all_records r
                ON r.stream=c.stream AND r.record_id=c.record_id WHERE ''' + current_where + ' LIMIT 1',
                current_args).fetchone() if current_where is not None else False,
        ))
        return SourceStateMaintenance(stream, policy.through, policy.disposition, records=len(rows),
            authority=len(authorities), retention_links=len(links), has_more=has_more,
            history_retained_after=self._history_floor(stream), retired_current=len(retired_current))

    def storage_usage(self):
        """Logical limits and actual SQLite sidecar bytes are distinct measures."""
        with self._lock:
            hot = self._db.execute('SELECT count,bytes FROM usage WHERE singleton=1').fetchone()
            cold = self._db.execute('SELECT count,bytes FROM cold_usage WHERE singleton=1').fetchone()
            page_size = self._db.execute('PRAGMA page_size').fetchone()[0]
            free_pages = self._db.execute('PRAGMA freelist_count').fetchone()[0]
            physical = {suffix or 'database': Path(str(self.path) + suffix).stat().st_size
                        if Path(str(self.path) + suffix).exists() else 0 for suffix in ('', '-wal', '-shm')}
        return {'hot_records': hot[0], 'hot_bytes': hot[1], 'archive_records': cold[0], 'archive_bytes': cold[1],
                'max_hot_records': self.max_records, 'max_hot_bytes': self.max_bytes,
                'max_archive_records': self.max_archive_records, 'max_archive_bytes': self.max_archive_bytes,
                'reusable_database_bytes': free_pages * page_size, 'physical_bytes': physical}

    def recovery_metadata(self):
        with self._lock:
            count = self._db.execute('SELECT count(*) FROM checkpoints').fetchone()[0]
            if count > 10000:
                raise ValueError('source_state.recovery_stream_limit')
            from .sqlite import _decode
            checkpoints = [_decode(row[0]) for row in self._db.execute('SELECT payload FROM checkpoints ORDER BY stream')]
            return {'provider_id': self.provider_id, 'checkpoints': tuple(checkpoints),
                    'usage': self.storage_usage(), 'history_horizons': dict(self._db.execute('SELECT * FROM history_horizons')),
                    'limits': {name: getattr(self, name) for name in ('max_records', 'max_bytes', 'max_record_bytes',
                        'max_archive_records', 'max_archive_bytes')}}

    def retained_references(self, *, page_size=256):
        """Stream dependencies under a host-owned quiescent recovery cut."""
        from .sqlite import _decode
        if type(page_size) is not int or not 1 <= page_size <= 10000:
            raise ValueError('source_state.page_invalid')
        after = ('', '')
        while True:
            with self._lock:
                rows = self._db.execute('''SELECT stream,record_id,payload FROM all_records
                    WHERE (stream,record_id)>(?,?) ORDER BY stream,record_id LIMIT ?''', (*after, page_size)).fetchall()
            if not rows:
                break
            for stream, identity, payload in rows:
                value = _decode(payload)
                reference = getattr(value, 'retained_reference', None)
                if reference is not None:
                    yield reference
            after = rows[-1][:2]
        after = ('', '')
        while True:
            with self._lock:
                rows = self._db.execute('''SELECT stream,accepted_id,payload FROM all_retention_links
                    WHERE (stream,accepted_id)>(?,?) ORDER BY stream,accepted_id LIMIT ?''', (*after, page_size)).fetchall()
            if not rows:
                break
            for _, _, payload in rows:
                yield _decode(payload)
            after = rows[-1][:2]
