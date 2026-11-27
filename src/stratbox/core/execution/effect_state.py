"""Atomic effect claims and exact, archive-transparent idempotency evidence."""
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from itertools import islice
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from uuid import uuid4
import json
import os
import re
import shutil
import sqlite3
import tempfile

from stratbox.shared.data.values import canonical_tree, restore_tree
from stratbox.core.storage.filestore import LocalFileStore
from .effect_evidence import same_effect_intent, valid_intent_update


_STATUSES = frozenset({"unknown", "confirmed", "rejected"})


def _positive(value, code, maximum=None):
    if type(value) is not int or value < 1 or maximum is not None and value > maximum:
        raise ValueError(code)
    return value


def _identity(value):
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError("effect.identity_invalid")
    return value


class FileEffectState:
    """SQLite arbitrates writers; cold bodies retain complete terminal receipts.

    Unknown effects and compact identity rows remain durable indefinitely. Archiving
    moves only terminal receipt bodies; missing cold evidence fails closed rather
    than making an effect appear unseen. The caller owns the storage lifecycle.
    """
    provider_id = "effects.sqlite"

    def __init__(self, directory, *, archive_directory=None, admitted_types=None,
                 max_receipt_bytes=16 * 1024 * 1024, max_hot_receipts=10000,
                 max_hot_bytes=64 * 1024 * 1024):
        _positive(max_receipt_bytes, "effect.receipt_limit_invalid")
        _positive(max_hot_receipts, "effect.hot_limit_invalid")
        _positive(max_hot_bytes, "effect.hot_limit_invalid")
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        database = self.directory / 'effects.sqlite'
        if not database.exists():
            # Unindexed evidence must never look like an unseen external effect.
            for entry in self.directory.iterdir():
                if (entry.is_dir() and len(entry.name) == 2
                        and all(character in '0123456789abcdef' for character in entry.name)):
                    raise ValueError('effect.unindexed_evidence_requires_explicit_storage')
            cold = self.directory / 'archive'
            if archive_directory is None and cold.exists() and next(cold.iterdir(), None) is not None:
                raise ValueError('effect.unindexed_evidence_requires_explicit_storage')
        self.archive_directory = Path(archive_directory).resolve() if archive_directory is not None else self.directory / "archive"
        self.archive_directory.mkdir(parents=True, exist_ok=True)
        self.store = LocalFileStore(str(self.archive_directory))
        self.admitted_types = MappingProxyType(dict(admitted_types or {}))
        self.max_receipt_bytes, self._lock = max_receipt_bytes, RLock()
        self.max_hot_receipts, self.max_hot_bytes = max_hot_receipts, max_hot_bytes
        self._database = database
        with self._connect() as db:
            db.execute("PRAGMA auto_vacuum=INCREMENTAL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS state_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO state_identity VALUES ('identity',?)", (uuid4().hex,))
            db.execute("INSERT OR IGNORE INTO state_identity VALUES ('archive_root',?)", (str(self.archive_directory),))
            db.execute("INSERT OR IGNORE INTO state_identity VALUES ('namespace_state','open')")
            db.execute("INSERT OR IGNORE INTO state_identity VALUES ('receipt_ceiling',?)", (str(max_receipt_bytes),))
            if db.execute("SELECT value FROM state_identity WHERE key='receipt_ceiling'").fetchone()[0] != str(max_receipt_bytes):
                raise ValueError('effect.receipt_limit_scope_conflict')
            self.scope_id = db.execute("SELECT value FROM state_identity WHERE key='identity'").fetchone()[0]
            if db.execute("SELECT value FROM state_identity WHERE key='archive_root'").fetchone()[0] != str(self.archive_directory):
                raise ValueError("effect.archive_scope_conflict")
            db.execute("""CREATE TABLE IF NOT EXISTS receipts (
                effect_id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                resource TEXT, finding TEXT, body BLOB, archive_locator TEXT,
                body_identity TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
                CHECK ((body IS NULL) != (archive_locator IS NULL)))""")
            if 'revision' not in {row[1] for row in db.execute('PRAGMA table_info(receipts)')}:
                # Preserve prior unknown/terminal identity when adding the
                # indexed cut revision. Migration visits bounded receipt pages.
                db.execute('ALTER TABLE receipts ADD COLUMN revision INTEGER NOT NULL DEFAULT 0')
                cursor = db.execute('SELECT * FROM receipts ORDER BY effect_id')
                while rows := cursor.fetchmany(256):
                    for row in rows:
                        receipt = self._receipt(row)
                        db.execute('UPDATE receipts SET revision=? WHERE effect_id=?', (receipt.revision, receipt.effect_id))
            db.execute("CREATE INDEX IF NOT EXISTS receipts_page ON receipts(status,effect_id)")
            db.execute("CREATE TABLE IF NOT EXISTS hot_usage (id INTEGER PRIMARY KEY CHECK(id=1), receipts INTEGER NOT NULL, bytes INTEGER NOT NULL)")
            if db.execute("SELECT 1 FROM hot_usage WHERE id=1").fetchone() is None:
                db.execute("INSERT INTO hot_usage SELECT 1,count(*),coalesce(sum(length(body)),0) FROM receipts WHERE body IS NOT NULL")
            db.execute('CREATE TABLE IF NOT EXISTS unknown_usage (id INTEGER PRIMARY KEY CHECK(id=1), receipts INTEGER NOT NULL, bytes INTEGER NOT NULL)')
            if db.execute('SELECT 1 FROM unknown_usage WHERE id=1').fetchone() is None:
                db.execute("INSERT INTO unknown_usage SELECT 1,count(*),coalesce(sum(length(body)),0) FROM receipts WHERE status='unknown'")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self._database, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _encode(self, receipt):
        _identity(receipt.effect_id)
        if not isinstance(receipt.kind, str) or not receipt.kind or len(receipt.kind) > 256 or receipt.status not in _STATUSES:
            raise ValueError("effect.receipt_invalid")
        if any(value is not None and (not isinstance(value, str) or len(value) > 4096)
               for value in (receipt.resource, receipt.finding)):
            raise ValueError("effect.receipt_metadata_invalid")
        if type(receipt.revision) is not int or receipt.revision < 0 or (
                receipt.claim_id is not None and (not isinstance(receipt.claim_id, str)
                or not receipt.claim_id or len(receipt.claim_id) > 128)):
            raise ValueError('effect.claim_invalid')
        obj = dict(effect_id=receipt.effect_id, kind=receipt.kind, status=receipt.status,
            value=canonical_tree(receipt.value), resource=receipt.resource,
            finding=receipt.finding, intent=canonical_tree(receipt.intent),
            revision=receipt.revision, claim_id=receipt.claim_id, evidence=canonical_tree(receipt.evidence))
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        if len(raw) > self.max_receipt_bytes:
            raise ValueError("effect.receipt_size_limit")
        # Reject an unreplayable acknowledgement before treating it as durable.
        self._decode(raw)
        return raw

    def _decode(self, raw):
        from .service import EffectReceipt
        if len(raw) > self.max_receipt_bytes:
            raise ValueError("effect.receipt_size_limit")
        obj = json.loads(raw)
        return EffectReceipt(obj["effect_id"], obj["kind"], obj["status"],
            restore_tree(obj["value"], admitted_types=self.admitted_types), obj["resource"],
            obj["finding"], restore_tree(obj["intent"], admitted_types=self.admitted_types),
            revision=obj.get('revision', 0), claim_id=obj.get('claim_id'),
            evidence=restore_tree(obj.get('evidence'), admitted_types=self.admitted_types))

    def _receipt(self, row):
        if row is None:
            return None
        raw = row["body"]
        if raw is None:
            with self.store.open_read(row["archive_locator"]) as stream:
                raw = stream.read(self.max_receipt_bytes + 1)
        if sha256(raw).hexdigest() != row["body_identity"]:
            raise ValueError("effect.receipt_identity_conflict")
        receipt = self._decode(raw)
        if (receipt.effect_id, receipt.kind, receipt.status, receipt.resource, receipt.finding) != tuple(row[key]
                for key in ("effect_id", "kind", "status", "resource", "finding")):
            raise ValueError("effect.identity_conflict")
        return receipt

    def _row(self, db, effect_id):
        return db.execute("SELECT * FROM receipts WHERE effect_id=?", (effect_id,)).fetchone()

    def _write(self, db, receipt, raw):
        previous = db.execute("SELECT length(body) AS size,status FROM receipts WHERE effect_id=?", (receipt.effect_id,)).fetchone()
        previous_size = None if previous is None else previous["size"]
        usage = db.execute("SELECT receipts,bytes FROM hot_usage WHERE id=1").fetchone()
        count = usage["receipts"] + (previous_size is None)
        size = usage["bytes"] - (previous_size or 0) + len(raw)
        unknown = db.execute('SELECT receipts,bytes FROM unknown_usage WHERE id=1').fetchone()
        was_unknown = previous is not None and previous['status'] == 'unknown'
        is_unknown = receipt.status == 'unknown'
        unknown_count = unknown['receipts'] - was_unknown + is_unknown
        unknown_bytes = unknown['bytes'] - (previous_size if was_unknown else 0) + (len(raw) if is_unknown else 0)
        reserved = unknown_count * self.max_receipt_bytes - unknown_bytes
        old_effective = usage['bytes'] + unknown['receipts'] * self.max_receipt_bytes - unknown['bytes']
        if (count > self.max_hot_receipts and count > usage['receipts']
                or size + reserved > self.max_hot_bytes and size + reserved > old_effective):
            raise RuntimeError("effect.hot_capacity_exhausted")
        db.execute("UPDATE hot_usage SET receipts=?,bytes=? WHERE id=1", (count, size))
        db.execute('UPDATE unknown_usage SET receipts=?,bytes=? WHERE id=1', (unknown_count, unknown_bytes))
        db.execute("""INSERT INTO receipts(effect_id,kind,status,resource,finding,body,archive_locator,body_identity,revision)
            VALUES (?,?,?,?,?,?,NULL,?,?)
            ON CONFLICT(effect_id) DO UPDATE SET kind=excluded.kind,status=excluded.status,
            resource=excluded.resource,finding=excluded.finding,body=excluded.body,
            archive_locator=NULL,body_identity=excluded.body_identity,revision=excluded.revision""",
            (receipt.effect_id, receipt.kind, receipt.status, receipt.resource, receipt.finding,
             raw, sha256(raw).hexdigest(), receipt.revision))

    @staticmethod
    def _same_identity(previous, receipt):
        if previous is not None and (previous.kind, previous.resource) != (receipt.kind, receipt.resource):
            raise ValueError("effect.identity_conflict")

    @staticmethod
    def _namespace_open(db):
        return db.execute("SELECT value FROM state_identity WHERE key='namespace_state'").fetchone()[0] == 'open'

    def close_namespace(self, reason, *, recovery_manifest_id=None):
        """Fence new actions after rollback; old exact-ID evidence stays usable.

        Restoring a backup cannot establish that a missing newer occurrence was
        never attempted. Reconciliation can settle existing uncertainty, while
        this namespace cannot issue a fresh or rejected-action claim.
        """
        if not isinstance(reason, str) or not reason or len(reason) > 4096:
            raise ValueError('effect.recovery_reason_invalid')
        if recovery_manifest_id is not None:
            _identity(recovery_manifest_id)
        with self._lock, self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for key, value in (('namespace_state', 'closed'), ('recovery_reason', reason),
                               ('recovery_manifest_id', recovery_manifest_id or '')):
                db.execute('INSERT INTO state_identity VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))

    def recovery_metadata(self):
        """Bounded metadata and SQL counts; complete bodies remain separately owned."""
        with self._lock, self._connect() as db:
            state = dict(db.execute('SELECT key,value FROM state_identity'))
            counts = {row[0]: row[1] for row in db.execute('SELECT status,count(*) FROM receipts GROUP BY status')}
            cold = db.execute('SELECT count(*) FROM receipts WHERE archive_locator IS NOT NULL').fetchone()[0]
            revision_sum = db.execute('SELECT coalesce(sum(revision),0) FROM receipts').fetchone()[0]
            hot = db.execute('SELECT receipts,bytes FROM hot_usage WHERE id=1').fetchone()
            unknown = db.execute('SELECT receipts,bytes FROM unknown_usage WHERE id=1').fetchone()
            reserved = unknown['receipts'] * self.max_receipt_bytes - unknown['bytes']
        return MappingProxyType({'provider_id': self.provider_id, 'scope_id': self.scope_id,
            'namespace_state': state['namespace_state'], 'recovery_reason': state.get('recovery_reason'),
            'recovery_manifest_id': state.get('recovery_manifest_id') or None,
            'unknown_count': counts.get('unknown', 0), 'confirmed_count': counts.get('confirmed', 0),
            'rejected_count': counts.get('rejected', 0), 'archived_count': cold,
            'revision_sum': revision_sum,
            'database': str(self._database), 'archive_directory': str(self.archive_directory),
            'max_receipt_bytes': self.max_receipt_bytes, 'hot_bytes': hot['bytes'],
            'reserved_bytes': reserved, 'effective_hot_bytes': hot['bytes'] + reserved,
            'max_hot_bytes': self.max_hot_bytes})

    @staticmethod
    def _file_identity(path):
        digest, size = sha256(), 0
        with Path(path).open('rb') as stream:
            while chunk := stream.read(65536):
                digest.update(chunk)
                size += len(chunk)
        return digest.hexdigest(), size

    @staticmethod
    def _cold_locator(locator, identity):
        if (not isinstance(identity, str) or re.fullmatch(r'[0-9a-f]{64}', identity) is None
                or locator != f'{identity[:2]}/{identity[2:4]}/{identity}'):
            raise ValueError('effect.archive_locator_invalid')
        return locator

    def export_checkpoint(self, destination, *, max_bytes=None, max_files=None, max_file_bytes=None):
        """Export a pinned database plus all immutable cold receipt dependencies.

        SQLite backup supplies one database cut. Receipt bodies referenced by
        that cut are immutable and never pruned by this provider. The streaming
        index avoids a manifest whose resident size grows with receipt count.
        """
        destination = Path(destination).resolve()
        for value in (max_bytes, max_files, max_file_bytes):
            if value is not None:
                _positive(value, 'effect.checkpoint_limit_invalid')
        if max_files is not None and max_files < 3:
            raise ValueError('effect.checkpoint_capacity_exhausted')
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='stratbox-effects-checkpoint-', dir=destination.parent))
        try:
            snapshot = temporary / 'effects.sqlite'
            with self._lock, self._connect() as source, sqlite3.connect(snapshot) as backup:
                page_size = source.execute('PRAGMA page_size').fetchone()[0]
                def bounded_backup(status, remaining, total):
                    size = total * page_size
                    if max_bytes is not None and size > max_bytes or max_file_bytes is not None and size > max_file_bytes:
                        raise ValueError('effect.checkpoint_capacity_exhausted')
                bounded_backup(0, 0, source.execute('PRAGMA page_count').fetchone()[0])
                source.backup(backup, pages=128, progress=bounded_backup)
                if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('effect.checkpoint_integrity_failed')
            count, total, index_size = 0, snapshot.stat().st_size, 0
            with sqlite3.connect(snapshot) as db, (temporary / 'cold-index.jsonl').open('wb') as index:
                db.row_factory = sqlite3.Row
                cursor = db.execute('SELECT * FROM receipts ORDER BY effect_id')
                while rows := cursor.fetchmany(256):
                    for row in rows:
                        # Validate hot and cold payload identities and typed
                        # replayability before publishing this checkpoint.
                        receipt = self._receipt(row)
                        if row['body'] is not None:
                            continue
                        locator = self._cold_locator(row['archive_locator'], row['body_identity'])
                        source = self.archive_directory / locator
                        target = temporary / 'archive' / locator
                        size = source.stat().st_size
                        if (max_files is not None and count + 4 > max_files
                                or max_file_bytes is not None and size > max_file_bytes
                                or max_bytes is not None and total + index_size + size > max_bytes):
                            raise ValueError('effect.checkpoint_capacity_exhausted')
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with source.open('rb') as incoming, target.open('xb') as outgoing:
                            shutil.copyfileobj(incoming, outgoing, 65536)
                            outgoing.flush()
                            os.fsync(outgoing.fileno())
                        identity, size = self._file_identity(target)
                        if identity != row['body_identity'] or size > self.max_receipt_bytes:
                            raise ValueError('effect.checkpoint_dependency_conflict')
                        line = (json.dumps({'effect_id': receipt.effect_id, 'locator': locator,
                            'sha256': identity, 'size': size}, sort_keys=True) + '\n').encode()
                        index_size += len(line)
                        total += size
                        if (max_file_bytes is not None and index_size > max_file_bytes
                                or max_bytes is not None and total + index_size > max_bytes):
                            raise ValueError('effect.checkpoint_capacity_exhausted')
                        index.write(line)
                        count += 1
                index.flush()
                os.fsync(index.fileno())
                state = dict(db.execute('SELECT key,value FROM state_identity'))
            (temporary / 'archive').mkdir(exist_ok=True)
            manifest = {'format': 'stratbox.effects.checkpoint.v1', 'scope_id': state['identity'],
                'namespace_state': state['namespace_state'], 'cold_count': count,
                'database_sha256': self._file_identity(snapshot)[0],
                'cold_index_sha256': self._file_identity(temporary / 'cold-index.jsonl')[0],
                'max_receipt_bytes': self.max_receipt_bytes,
                'max_hot_receipts': self.max_hot_receipts, 'max_hot_bytes': self.max_hot_bytes}
            with (temporary / 'checkpoint.json').open('x', encoding='utf-8') as stream:
                encoded = json.dumps(manifest, sort_keys=True)
                if (max_bytes is not None and total + index_size + len(encoded.encode()) > max_bytes
                        or max_file_bytes is not None and len(encoded.encode()) > max_file_bytes):
                    raise ValueError('effect.checkpoint_capacity_exhausted')
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            if destination.exists():
                raise FileExistsError(destination)
            temporary.rename(destination)
            return MappingProxyType({**manifest, 'directory': str(destination),
                'database': str(destination / 'effects.sqlite'),
                'cold_index': str(destination / 'cold-index.jsonl')})
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    @classmethod
    def checkpoint_view(cls, checkpoint_directory, *, admitted_types=None):
        """Read bounded exact receipts from a checkpoint without restoring it."""
        return _EffectCheckpointView(checkpoint_directory, admitted_types=admitted_types)

    @classmethod
    def restore_checkpoint(cls, checkpoint_directory, destination, *, recovery_manifest_id=None,
                           admitted_types=None):
        """Restore exact evidence into a new location with new actions fenced."""
        checkpoint, destination = Path(checkpoint_directory).resolve(), Path(destination).resolve()
        if destination.exists():
            raise FileExistsError(destination)
        with (checkpoint / 'checkpoint.json').open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('effect.checkpoint_manifest_limit')
        manifest = json.loads(raw)
        if manifest.get('format') != 'stratbox.effects.checkpoint.v1':
            raise ValueError('effect.checkpoint_format_invalid')
        if (cls._file_identity(checkpoint / 'effects.sqlite')[0] != manifest['database_sha256']
                or cls._file_identity(checkpoint / 'cold-index.jsonl')[0] != manifest['cold_index_sha256']):
            raise ValueError('effect.checkpoint_identity_conflict')
        for key in ('max_receipt_bytes', 'max_hot_receipts', 'max_hot_bytes'):
            _positive(manifest[key], 'effect.checkpoint_limit_invalid')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='stratbox-effects-restore-', dir=destination.parent))
        try:
            shutil.copyfile(checkpoint / 'effects.sqlite', temporary / 'effects.sqlite')
            archive = temporary / 'archive'
            archive.mkdir()
            with sqlite3.connect(temporary / 'effects.sqlite') as db, (checkpoint / 'cold-index.jsonl').open('rb') as index:
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('effect.checkpoint_integrity_failed')
                if db.execute("SELECT value FROM state_identity WHERE key='identity'").fetchone()[0] != manifest['scope_id']:
                    raise ValueError('effect.checkpoint_scope_conflict')
                count = 0
                rows = db.execute('SELECT effect_id,archive_locator,body_identity FROM receipts WHERE body IS NULL ORDER BY effect_id')
                for effect_id, locator, identity in rows:
                    raw = index.readline(16385)
                    if not raw or len(raw) > 16384:
                        raise ValueError('effect.checkpoint_dependency_index_invalid')
                    item = json.loads(raw)
                    cls._cold_locator(locator, identity)
                    if (item['effect_id'], item['locator'], item['sha256']) != (effect_id, locator, identity):
                        raise ValueError('effect.checkpoint_dependency_conflict')
                    incoming, outgoing = checkpoint / 'archive' / locator, archive / locator
                    if cls._file_identity(incoming) != (identity, item['size']) or item['size'] > manifest['max_receipt_bytes']:
                        raise ValueError('effect.checkpoint_dependency_conflict')
                    outgoing.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(incoming, outgoing)
                    count += 1
                if index.read(1) or count != manifest['cold_count']:
                    raise ValueError('effect.checkpoint_dependency_index_invalid')
                # Relocation is an explicit restore operation. Keep the scope
                # identity and every occurrence, changing only local paths and
                # the persisted fence before the directory can be opened.
                values = {'archive_root': str(temporary / 'archive'), 'namespace_state': 'closed',
                    'recovery_reason': 'Restored checkpoint may omit newer external occurrences',
                    'recovery_manifest_id': recovery_manifest_id or ''}
                for key, value in values.items():
                    db.execute('INSERT INTO state_identity VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
            candidate = cls(temporary, admitted_types=admitted_types,
                max_receipt_bytes=manifest['max_receipt_bytes'], max_hot_receipts=manifest['max_hot_receipts'],
                max_hot_bytes=manifest['max_hot_bytes'])
            # Validate both typed hot and cold bodies before publication. A
            # missing admitted codec leaves no apparently resumable owner.
            with candidate._connect() as db:
                cursor = db.execute('SELECT * FROM receipts ORDER BY effect_id')
                while rows := cursor.fetchmany(256):
                    for row in rows:
                        candidate._receipt(row)
                db.execute("UPDATE state_identity SET value=? WHERE key='archive_root'", (str(destination / 'archive'),))
            if destination.exists():
                raise FileExistsError(destination)
            temporary.rename(destination)
            return cls(destination, admitted_types=admitted_types,
                max_receipt_bytes=manifest['max_receipt_bytes'], max_hot_receipts=manifest['max_hot_receipts'],
                max_hot_bytes=manifest['max_hot_bytes'])
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    def get(self, effect_id):
        _identity(effect_id)
        with self._lock, self._connect() as db:
            return self._receipt(self._row(db, effect_id))

    def begin(self, receipt):
        """Atomically claim a fresh/rejected effect before calling its external action."""
        if receipt.status != "unknown":
            raise ValueError("effect.unknown_claim_required")
        self._encode(receipt)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = self._receipt(self._row(db, receipt.effect_id))
            self._same_identity(previous, receipt)
            if previous is not None and not same_effect_intent(previous.intent, receipt.intent):
                raise ValueError('effect.intent_conflict')
            if previous is not None and previous.status in {"unknown", "confirmed"}:
                return previous, False
            if not self._namespace_open(db):
                raise ValueError('effect.recovery_namespace_closed')
            receipt = replace(receipt, revision=1 if previous is None else previous.revision + 1, claim_id=uuid4().hex)
            raw = self._encode(receipt)
            self._write(db, receipt, raw)
            return self._decode(raw), True

    def put(self, receipt):
        """Persist intent enrichment or settlement without erasing a confirmation."""
        self._encode(receipt)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._row(db, receipt.effect_id)
            previous = self._receipt(row)
            self._same_identity(previous, receipt)
            if previous is not None and previous.status == "confirmed":
                if replace(receipt, revision=0, claim_id=None) != replace(previous, revision=0, claim_id=None):
                    raise ValueError("effect.confirmed_conflict")
                return previous
            if previous is not None and previous.status == "rejected" and receipt.status != "rejected":
                raise ValueError("effect.atomic_begin_required")
            if previous is not None:
                if (receipt.revision, receipt.claim_id) != (previous.revision, previous.claim_id):
                    raise ValueError('effect.stale_revision_or_claim')
                if not valid_intent_update(previous.intent, receipt.intent):
                    raise ValueError('effect.intent_conflict')
                if receipt == previous:
                    return previous
            elif not self._namespace_open(db):
                raise ValueError('effect.recovery_namespace_closed')
            receipt = replace(receipt, revision=1 if previous is None else previous.revision + 1)
            raw = self._encode(receipt)
            self._write(db, receipt, raw)
            return self._decode(raw)

    def usage(self):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT receipts,bytes FROM hot_usage WHERE id=1").fetchone()
            unknown = db.execute('SELECT receipts,bytes FROM unknown_usage WHERE id=1').fetchone()
            reserved = unknown['receipts'] * self.max_receipt_bytes - unknown['bytes']
            return MappingProxyType({"hot_receipts": row["receipts"], "hot_bytes": row["bytes"],
                'unknown_receipts': unknown['receipts'], 'reserved_bytes': reserved,
                'effective_hot_bytes': row['bytes'] + reserved,
                "max_hot_receipts": self.max_hot_receipts, "max_hot_bytes": self.max_hot_bytes})

    def page(self, *, after="", limit=1000, status=None, archived=None):
        """Read bounded identity summaries; retrieve complete bodies explicitly with get."""
        _positive(limit, "effect.page_limit_invalid", maximum=10000)
        if not isinstance(after, str) or status is not None and status not in _STATUSES or archived is not None and type(archived) is not bool:
            raise ValueError("effect.page_invalid")
        where, args = ["effect_id > ?"], [after]
        if status is not None:
            where.append("status = ?"); args.append(status)
        if archived is not None:
            where.append("body IS NULL" if archived else "body IS NOT NULL")
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT effect_id,kind,status,resource,finding,body_identity,body IS NULL AS archived FROM receipts WHERE "
                + " AND ".join(where) + " ORDER BY effect_id LIMIT ?", (*args, limit)).fetchall()
            return tuple(MappingProxyType({**dict(row), "archived": bool(row["archived"])}) for row in rows)

    def archive(self, effect_ids):
        """Move an explicit bounded set of terminal bodies into immutable cold storage."""
        if isinstance(effect_ids, (str, bytes)):
            raise ValueError("effect.archive_ids_invalid")
        identities = tuple(islice(effect_ids, 10001))
        if not identities or len(identities) > 10000 or len(set(identities)) != len(identities):
            raise ValueError("effect.archive_ids_invalid")
        for identity in identities:
            _identity(identity)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = [db.execute("SELECT effect_id,status FROM receipts WHERE effect_id=?", (identity,)).fetchone() for identity in identities]
            if any(row is None for row in rows):
                raise ValueError("effect.archive_identity_missing")
            if any(row["status"] == "unknown" for row in rows):
                raise ValueError("effect.unknown_retention_required")
            archived = []
            for summary in rows:
                row = self._row(db, summary["effect_id"])
                # Validate existing archive evidence as well: an unreadable tombstone
                # never grants permission to rerun or silently forget an effect.
                self._receipt(row)
                if row["body"] is not None:
                    identity = row["body_identity"]
                    locator = f"{identity[:2]}/{identity[2:4]}/{identity}"
                    self.store.create_immutable(locator, row["body"])
                    db.execute("UPDATE receipts SET body=NULL,archive_locator=? WHERE effect_id=?", (locator, row["effect_id"]))
                    db.execute("UPDATE hot_usage SET receipts=receipts-1,bytes=bytes-? WHERE id=1", (len(row["body"]),))
                archived.append(row["effect_id"])
            return tuple(archived)

    def compact(self, *, pages=1000):
        """Release a bounded number of unused hot pages; all identity rows remain."""
        _positive(pages, "effect.compaction_limit_invalid", maximum=100000)
        with self._lock, self._connect() as db:
            db.execute(f"PRAGMA incremental_vacuum({pages})")
            return MappingProxyType({"free_pages": db.execute("PRAGMA freelist_count").fetchone()[0],
                "page_count": db.execute("PRAGMA page_count").fetchone()[0]})


class _EffectCheckpointView:
    """Only get/page are exposed; SQLite opens the snapshot in read-only mode."""
    def __init__(self, directory, *, admitted_types=None):
        self.directory = Path(directory).resolve()
        self._database = self.directory / 'effects.sqlite'
        with (self.directory / 'checkpoint.json').open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('effect.checkpoint_manifest_limit')
        manifest = json.loads(raw)
        if (manifest.get('format') != 'stratbox.effects.checkpoint.v1'
                or FileEffectState._file_identity(self._database)[0] != manifest['database_sha256']
                or FileEffectState._file_identity(self.directory / 'cold-index.jsonl')[0] != manifest['cold_index_sha256']):
            raise ValueError('effect.checkpoint_identity_conflict')
        self.scope_id, self.max_receipt_bytes = manifest['scope_id'], manifest['max_receipt_bytes']
        _identity(self.scope_id)
        _positive(self.max_receipt_bytes, 'effect.checkpoint_limit_invalid')
        self.admitted_types, self._lock = MappingProxyType(dict(admitted_types or {})), RLock()
        self.archive_directory = self.directory / 'archive'
        self.store = LocalFileStore(self.archive_directory)
        with self._connect() as db:
            if db.execute("SELECT value FROM state_identity WHERE key='identity'").fetchone()[0] != self.scope_id:
                raise ValueError('effect.checkpoint_scope_conflict')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self._database.as_uri() + '?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    _decode = FileEffectState._decode
    _receipt = FileEffectState._receipt
    _row = FileEffectState._row
    get = FileEffectState.get
    page = FileEffectState.page
