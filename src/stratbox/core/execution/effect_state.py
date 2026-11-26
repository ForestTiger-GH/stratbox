"""Atomic effect claims and exact, archive-transparent idempotency evidence."""
from collections.abc import Mapping
from contextlib import contextmanager
from hashlib import sha256
from itertools import islice
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from uuid import uuid4
import json
import sqlite3

from stratbox.shared.data.values import canonical_tree, restore_tree
from stratbox.core.storage.filestore import LocalFileStore


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
            self.scope_id = db.execute("SELECT value FROM state_identity WHERE key='identity'").fetchone()[0]
            if db.execute("SELECT value FROM state_identity WHERE key='archive_root'").fetchone()[0] != str(self.archive_directory):
                raise ValueError("effect.archive_scope_conflict")
            db.execute("""CREATE TABLE IF NOT EXISTS receipts (
                effect_id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                resource TEXT, finding TEXT, body BLOB, archive_locator TEXT,
                body_identity TEXT NOT NULL,
                CHECK ((body IS NULL) != (archive_locator IS NULL)))""")
            db.execute("CREATE INDEX IF NOT EXISTS receipts_page ON receipts(status,effect_id)")
            db.execute("CREATE TABLE IF NOT EXISTS hot_usage (id INTEGER PRIMARY KEY CHECK(id=1), receipts INTEGER NOT NULL, bytes INTEGER NOT NULL)")
            if db.execute("SELECT 1 FROM hot_usage WHERE id=1").fetchone() is None:
                db.execute("INSERT INTO hot_usage SELECT 1,count(*),coalesce(sum(length(body)),0) FROM receipts WHERE body IS NOT NULL")

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
        obj = dict(effect_id=receipt.effect_id, kind=receipt.kind, status=receipt.status,
            value=canonical_tree(receipt.value), resource=receipt.resource,
            finding=receipt.finding, intent=canonical_tree(receipt.intent))
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
            obj["finding"], restore_tree(obj["intent"], admitted_types=self.admitted_types))

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
        previous = db.execute("SELECT length(body) AS size FROM receipts WHERE effect_id=?", (receipt.effect_id,)).fetchone()
        previous_size = None if previous is None else previous["size"]
        usage = db.execute("SELECT receipts,bytes FROM hot_usage WHERE id=1").fetchone()
        count = usage["receipts"] + (previous_size is None)
        size = usage["bytes"] - (previous_size or 0) + len(raw)
        if count > self.max_hot_receipts or size > self.max_hot_bytes:
            raise RuntimeError("effect.hot_capacity_exhausted")
        db.execute("UPDATE hot_usage SET receipts=?,bytes=? WHERE id=1", (count, size))
        db.execute("""INSERT INTO receipts VALUES (?,?,?,?,?,?,NULL,?)
            ON CONFLICT(effect_id) DO UPDATE SET kind=excluded.kind,status=excluded.status,
            resource=excluded.resource,finding=excluded.finding,body=excluded.body,
            archive_locator=NULL,body_identity=excluded.body_identity""",
            (receipt.effect_id, receipt.kind, receipt.status, receipt.resource, receipt.finding,
             raw, sha256(raw).hexdigest()))

    @staticmethod
    def _same_identity(previous, receipt):
        if previous is not None and (previous.kind, previous.resource) != (receipt.kind, receipt.resource):
            raise ValueError("effect.identity_conflict")

    def get(self, effect_id):
        _identity(effect_id)
        with self._lock, self._connect() as db:
            return self._receipt(self._row(db, effect_id))

    def begin(self, receipt):
        """Atomically claim a fresh/rejected effect before calling its external action."""
        if receipt.status != "unknown":
            raise ValueError("effect.unknown_claim_required")
        raw = self._encode(receipt)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = self._receipt(self._row(db, receipt.effect_id))
            self._same_identity(previous, receipt)
            if previous is not None and previous.status in {"unknown", "confirmed"}:
                return previous, False
            self._write(db, receipt, raw)
            return self._decode(raw), True

    def put(self, receipt):
        """Persist intent enrichment or settlement without erasing a confirmation."""
        raw = self._encode(receipt)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._row(db, receipt.effect_id)
            previous = self._receipt(row)
            self._same_identity(previous, receipt)
            if previous is not None and previous.status == "confirmed":
                if sha256(raw).hexdigest() != row["body_identity"]:
                    raise ValueError("effect.confirmed_conflict")
                return
            if previous is not None and previous.status == "rejected" and receipt.status != "rejected":
                raise ValueError("effect.atomic_begin_required")
            self._write(db, receipt, raw)

    def usage(self):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT receipts,bytes FROM hot_usage WHERE id=1").fetchone()
            return MappingProxyType({"hot_receipts": row["receipts"], "hot_bytes": row["bytes"],
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
