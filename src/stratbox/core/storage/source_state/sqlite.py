"""Transactional persistent projection with indexed keys and bounded pages."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from threading import RLock

from stratbox.shared.data.values import canonical_tree, restore_tree
from stratbox.shared.data.processing import RetainedOutput, SourceObservation, SourceStateSnapshot, StateProjectionCheckpoint
from .ports import normalize_keys, validate_page, next_checkpoint, record_id, current_key, current_order, linked_output
from .sqlite_retention import SQLiteRetention


def _encode(value):
    return json.dumps(canonical_tree(value), sort_keys=True, separators=(',', ':'))


def _decode(value):
    return restore_tree(json.loads(value))


class SQLiteSourceState(SQLiteRetention):
    provider_id = 'source_state.sqlite'

    def __init__(self, path, *, max_records=1000000, max_bytes=512 * 1024 * 1024,
                 max_record_bytes=1024 * 1024, max_archive_records=10000000,
                 max_archive_bytes=4 * 1024 * 1024 * 1024):
        if any(type(value) is not int or value < 1 for value in (max_records, max_bytes, max_record_bytes,
                                                              max_archive_records, max_archive_bytes)):
            raise ValueError('source_state.limits_invalid')
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_records, self.max_bytes, self.max_record_bytes = max_records, max_bytes, max_record_bytes
        self.max_archive_records, self.max_archive_bytes = max_archive_records, max_archive_bytes
        self._lock = RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._db.execute('PRAGMA journal_mode=WAL')
        self._db.execute('PRAGMA synchronous=FULL')
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS checkpoints(stream TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records(
                stream TEXT NOT NULL, record_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                source_id TEXT NOT NULL, issue_id TEXT, asset_id TEXT, record_kind TEXT NOT NULL,
                accepted_id TEXT, persistent INTEGER NOT NULL, payload TEXT NOT NULL,
                value_identity TEXT, represented_value_id TEXT, fold_key TEXT NOT NULL, current_at TEXT NOT NULL,
                PRIMARY KEY(stream, record_id));
            CREATE INDEX IF NOT EXISTS state_source_page ON records(stream, source_id, sequence, record_id);
            CREATE INDEX IF NOT EXISTS state_accepted ON records(stream, accepted_id);
            CREATE INDEX IF NOT EXISTS state_represented ON records(stream, represented_value_id);
            CREATE INDEX IF NOT EXISTS state_equivalent ON records(stream, fold_key, current_at, sequence);
            CREATE TABLE IF NOT EXISTS current_records(
                stream TEXT NOT NULL, fold_key TEXT NOT NULL, record_id TEXT NOT NULL,
                observed_at TEXT NOT NULL, sequence INTEGER NOT NULL, PRIMARY KEY(stream,fold_key));
            CREATE INDEX IF NOT EXISTS current_record_lookup ON current_records(stream,record_id);
            CREATE TABLE IF NOT EXISTS authority(
                stream TEXT NOT NULL, kind TEXT NOT NULL, identity TEXT NOT NULL, sequence INTEGER NOT NULL,
                PRIMARY KEY(stream, kind, identity));
            CREATE INDEX IF NOT EXISTS authority_lookup ON authority(kind, identity);
            CREATE TABLE IF NOT EXISTS retention_links(
                stream TEXT NOT NULL, accepted_id TEXT NOT NULL, payload TEXT NOT NULL, sequence INTEGER NOT NULL,
                PRIMARY KEY(stream, accepted_id));
            CREATE TABLE IF NOT EXISTS usage(singleton INTEGER PRIMARY KEY CHECK(singleton=1), count INTEGER NOT NULL, bytes INTEGER NOT NULL);
            INSERT OR IGNORE INTO usage VALUES(1,0,0);
        ''')
        if 'sequence' not in {row[1] for row in self._db.execute('PRAGMA table_info(retention_links)')}:
            # An older checkpoint did not retain the link's acceptance position.
            # Preserve it outside every finite retirement cut until rebuilt.
            self._db.execute('ALTER TABLE retention_links ADD COLUMN sequence INTEGER NOT NULL DEFAULT 9223372036854775807')
        self._initialize_retention()

    def checkpoint(self, stream_id):
        with self._lock:
            row = self._db.execute('SELECT payload FROM checkpoints WHERE stream=?', (stream_id,)).fetchone()
            return _decode(row[0]) if row else None

    def _reserve(self, old_size, new_size, *, added=False):
        if new_size > self.max_record_bytes:
            raise ValueError('source_state.record_limit')
        count, size = self._db.execute('SELECT count,bytes FROM usage WHERE singleton=1').fetchone()
        count, size = count + int(added), size + new_size - old_size
        if count > self.max_records or size > self.max_bytes:
            raise ValueError('source_state.capacity_exhausted')
        self._db.execute('UPDATE usage SET count=?,bytes=? WHERE singleton=1', (count, size))

    def apply_page(self, page, records=(), authority=(), retention_links=()):
        with self._lock:
            self._db.execute('BEGIN IMMEDIATE')
            try:
                previous = self.checkpoint(page.stream_id)
                applied = validate_page(page, previous)
                for value in records:
                    if value.sequence <= applied:
                        continue
                    if not page.after < value.sequence <= page.scanned_through:
                        raise ValueError('source_state.record_outside_page')
                    encoded, key = _encode(value), record_id(value)
                    cold = self._db.execute('SELECT * FROM cold_records WHERE stream=? AND record_id=?', (page.stream_id, key)).fetchone()
                    if cold is not None:
                        self._delete_row('records', cold, True)
                    row = self._db.execute('SELECT length(CAST(payload AS BLOB)) FROM records WHERE stream=? AND record_id=?', (page.stream_id, key)).fetchone()
                    self._reserve(row[0] if row else 0, len(encoded.encode()), added=row is None)
                    moment, sequence = current_order(value)
                    self._db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (page.stream_id, key, value.sequence, value.key.source_id, value.key.issue_id, value.key.asset_id,
                         type(value).__name__, getattr(value, 'accepted_value_id', None), int(getattr(value, 'persistent', False)), encoded,
                         getattr(value, 'value_identity', None), getattr(value, 'represents_value_identity', None),
                         current_key(value), moment.isoformat()))
                    self._db.execute('''INSERT INTO current_records VALUES(?,?,?,?,?)
                        ON CONFLICT(stream,fold_key) DO UPDATE SET record_id=excluded.record_id,
                        observed_at=excluded.observed_at,sequence=excluded.sequence
                        WHERE excluded.observed_at>current_records.observed_at
                        OR (excluded.observed_at=current_records.observed_at AND excluded.sequence>=current_records.sequence)''',
                        (page.stream_id, current_key(value), key, moment.isoformat(), sequence))
                    self._index_references(page.stream_id, key, value)
                for kind, identity, sequence in authority:
                    if sequence <= applied:
                        continue
                    if not page.after < sequence <= page.scanned_through or kind not in {'certificate', 'source_use', 'acquisition'}:
                        raise ValueError('source_state.authority_outside_page')
                    row = self._db.execute('SELECT 1 FROM all_authority WHERE stream=? AND kind=? AND identity=?', (page.stream_id, kind, identity)).fetchone()
                    if row is None:
                        self._reserve(0, len(kind.encode()) + len(identity.encode()) + 16, added=True)
                        self._db.execute('INSERT INTO authority VALUES(?,?,?,?)', (page.stream_id, kind, identity, sequence))
                for accepted_id, reference, sequence in retention_links:
                    if sequence <= applied:
                        continue
                    if not page.after < sequence <= page.scanned_through:
                        raise ValueError('source_state.retention_outside_page')
                    encoded = _encode(reference)
                    cold = self._db.execute('SELECT * FROM cold_retention_links WHERE stream=? AND accepted_id=?', (page.stream_id, accepted_id)).fetchone()
                    if cold is not None:
                        self._delete_row('retention_links', cold, True)
                    row = self._db.execute('SELECT length(CAST(payload AS BLOB)) FROM retention_links WHERE stream=? AND accepted_id=?', (page.stream_id, accepted_id)).fetchone()
                    self._reserve(row[0] if row else 0, len(encoded.encode()), added=row is None)
                    self._db.execute('INSERT OR REPLACE INTO retention_links VALUES(?,?,?,?)', (page.stream_id, accepted_id, encoded, sequence))
                checkpoint = next_checkpoint(page, previous)
                self._db.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?)', (page.stream_id, _encode(checkpoint)))
                self._db.execute('COMMIT')
                return checkpoint
            except BaseException:
                self._db.execute('ROLLBACK')
                raise

    def read(self, keys, *, stream_id, minimum_applied_through=0, limit=1000, after=None, view='current'):
        keys = normalize_keys(keys)
        if type(limit) is not int or not 1 <= limit <= 10000 or view not in {'current', 'history'}:
            raise ValueError('source_state.page_invalid')
        terms, arguments = [], [stream_id]
        for key in keys:
            clause = 'source_id=?'
            arguments.append(key.source_id)
            if key.issue_id is not None:
                clause += ' AND issue_id=?'
                arguments.append(key.issue_id)
            if key.asset_id is not None:
                clause += ' AND asset_id=?'
                arguments.append(key.asset_id)
            terms.append('(' + clause + ')')
        where = 'stream=? AND (' + (' OR '.join(terms) or '0') + ')'
        if view == 'current':
            where += ' AND EXISTS(SELECT 1 FROM current_records c WHERE c.stream=records.stream AND c.record_id=records.record_id)'
        if after is not None:
            if len(after) != 2 or type(after[0]) is not int or not isinstance(after[1], str):
                raise ValueError('source_state.cursor_invalid')
            where += ' AND (sequence>? OR (sequence=? AND record_id>?))'
            arguments.extend((after[0], after[0], after[1]))
        arguments.append(limit + 1)
        with self._lock:
            self._db.execute('BEGIN')
            try:
                checkpoint = self.checkpoint(stream_id) or StateProjectionCheckpoint(stream_id, 0, coverage_complete=False)
                rows = self._db.execute('SELECT sequence,record_id,payload FROM all_records AS records WHERE ' + where +
                    ' ORDER BY sequence,record_id LIMIT ?', arguments).fetchall()
                chosen, truncated = rows[:limit], len(rows) > limit
                outputs, observations = [], []
                for _, _, payload in chosen:
                    value = _decode(payload)
                    if isinstance(value, RetainedOutput):
                        resolved = self._resolve_output(stream_id, value)
                        if view == 'current' and not resolved.persistent:
                            equivalent = self._db.execute('''SELECT r.payload FROM all_records r
                                LEFT JOIN all_retention_links l ON l.stream=r.stream AND l.accepted_id=r.accepted_id
                                WHERE r.stream=? AND r.fold_key=? AND (r.persistent=1 OR l.payload IS NOT NULL
                                    OR EXISTS(SELECT 1 FROM all_records p LEFT JOIN all_retention_links pl
                                        ON pl.stream=p.stream AND pl.accepted_id=p.accepted_id
                                        WHERE p.stream=r.stream AND p.represented_value_id=r.value_identity
                                        AND (p.persistent=1 OR pl.payload IS NOT NULL)))
                                ORDER BY r.current_at DESC,r.sequence DESC LIMIT 1''',
                                (stream_id, current_key(value))).fetchone()
                            if equivalent:
                                resolved = self._resolve_output(stream_id, _decode(equivalent[0]))
                        outputs.append(resolved)
                    elif isinstance(value, SourceObservation):
                        observations.append(value)
                history_floor = self._history_floor(stream_id)
                self._db.execute('COMMIT')
            except BaseException:
                self._db.execute('ROLLBACK')
                raise
        return SourceStateSnapshot(keys, checkpoint, tuple(outputs), tuple(observations), minimum_applied_through,
                                   truncated, tuple(chosen[-1][:2]) if truncated else None, tuple(after) if after is not None else None,
                                   view, history_floor)

    def _resolve_output(self, stream_id, value):
        retained = self._db.execute('SELECT payload FROM all_retention_links WHERE stream=? AND accepted_id=?',
                                    (stream_id, value.accepted_value_id)).fetchone()
        links = {value.accepted_value_id: _decode(retained[0])} if retained else {}
        representations = []
        if not retained and value.retained_reference is None:
            represented = self._db.execute('''SELECT r.payload,l.payload FROM all_records r
                LEFT JOIN all_retention_links l ON l.stream=r.stream AND l.accepted_id=r.accepted_id
                WHERE r.stream=? AND r.represented_value_id=? AND (r.persistent=1 OR l.payload IS NOT NULL)
                ORDER BY r.sequence DESC LIMIT 1''', (stream_id, value.value_identity)).fetchone()
            if represented:
                representation = _decode(represented[0])
                representations.append(representation)
                if represented[1]:
                    links[representation.accepted_value_id] = _decode(represented[1])
        return linked_output(value, links, representations)

    def _has(self, kind, identity):
        with self._lock:
            return self._db.execute('SELECT 1 FROM all_authority WHERE kind=? AND identity=? LIMIT 1', (kind, identity)).fetchone() is not None

    def has_validation_certificate(self, identity):
        return self._has('certificate', identity)

    def has_source_use(self, identity):
        return self._has('source_use', identity)

    def has_acquisition_evidence(self, identity):
        return self._has('acquisition', identity)

    def compact(self, *, stream_id, through, limit=1000):
        """Prune diagnostic ephemeral outputs; retained inputs and observations survive."""
        with self._lock:
            checkpoint = self.checkpoint(stream_id)
            if (checkpoint is None or type(through) is not int or not 0 <= through <= checkpoint.applied_through
                    or type(limit) is not int or not 1 <= limit <= 10000):
                raise ValueError('source_state.compaction_cursor_invalid')
            self._db.execute('BEGIN IMMEDIATE')
            try:
                where = '''stream=? AND sequence<=? AND record_kind='RetainedOutput' AND persistent=0
                    AND NOT EXISTS(SELECT 1 FROM all_retention_links l WHERE l.stream=records.stream AND l.accepted_id=records.accepted_id)
                    AND NOT EXISTS(SELECT 1 FROM all_records r WHERE r.stream=records.stream AND r.represented_value_id=records.value_identity)'''
                rows = self._db.execute('SELECT * FROM records WHERE ' + where + ' ORDER BY sequence,record_id LIMIT ?',
                                         (stream_id, through, limit)).fetchall()
                affected = set()
                for row in rows:
                    self._delete_row('records', row, False)
                    self._db.execute('DELETE FROM authority_refs WHERE stream=? AND record_id=?', row[:2])
                    self._db.execute('DELETE FROM reference_index WHERE stream=? AND record_id=?', row[:2])
                    if self._db.execute('DELETE FROM current_records WHERE stream=? AND record_id=?', row[:2]).rowcount:
                        affected.add(row[12])
                for fold_key in affected:
                    previous = self._db.execute('SELECT record_id,current_at,sequence FROM all_records WHERE stream=? AND fold_key=? ORDER BY current_at DESC,sequence DESC LIMIT 1', (stream_id, fold_key)).fetchone()
                    if previous:
                        self._db.execute('INSERT OR REPLACE INTO current_records VALUES(?,?,?,?,?)', (stream_id, fold_key, *previous))
                if rows:
                    self._db.execute('''INSERT INTO history_horizons VALUES(?,?) ON CONFLICT(stream)
                        DO UPDATE SET retired_through=max(retired_through,excluded.retired_through)''',
                        (stream_id, max(row[2] for row in rows)))
                self._db.execute('COMMIT')
                return len(rows)
            except BaseException:
                self._db.execute('ROLLBACK')
                raise

    def export_checkpoint(self, destination, *, max_bytes=None):
        """Make a consistent SQLite checkpoint without a full in-memory dump."""
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
            raise ValueError('source_state.checkpoint_limit_invalid')
        destination = Path(destination).resolve()
        if destination == self.path or destination.exists():
            raise ValueError('source_state.checkpoint_destination_exists')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            page_size = self._db.execute('PRAGMA page_size').fetchone()[0]
            def check_size(_status, _remaining, total):
                if max_bytes is not None and total * page_size > max_bytes:
                    raise ValueError('source_state.checkpoint_size_limit')
            check_size(None, None, self._db.execute('PRAGMA page_count').fetchone()[0])
            target = sqlite3.connect(destination)
            try:
                self._db.backup(target, pages=64, progress=check_size)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('source_state.checkpoint_integrity')
            except BaseException:
                target.close()
                destination.unlink(missing_ok=True)
                raise
            finally:
                target.close()
        return str(destination)

    def close(self):
        with self._lock:
            self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
