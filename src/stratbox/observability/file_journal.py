"""Immutable, bounded file segments with qualified write and read-back receipts.

No concurrent append, arbitrary overwrite, implicit storage root, or claimed power-loss
survivability. A storage acknowledgement and a business-effect acknowledgement differ.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Iterable, Iterator, Protocol

from stratbox.base.filestore import FileStore
from stratbox.data import ByteIdentity
from stratbox.execution.contracts import safe_token

from .codecs import JournalDecodeError, decode_records, encode_records, iter_decode_jsonl
from .contracts import JournalBarrierError, JournalRecord, JournalWriteReceipt
from .policies import PersistencePolicy


class RecordWriter(Protocol):
    def write_batch(self, records: Iterable[JournalRecord], *, segment_id: str | None = None) -> JournalWriteReceipt: ...


class RecordReader(Protocol):
    def iter_segments(self, paths: Iterable[str], *, expected: dict[str, ByteIdentity] | None = None) -> Iterator[JournalRecord]: ...


@dataclass(frozen=True, slots=True)
class JournalReadIssue:
    locator: str
    code: str
    line: int | None = None


@dataclass(frozen=True, slots=True)
class JournalReadReport:
    records: tuple[JournalRecord, ...]
    issues: tuple[JournalReadIssue, ...]
    complete: bool


def _read_exact(store: FileStore, path: str, expected: ByteIdentity, *, max_bytes: int) -> str:
    """Read-back result: match, missing, mismatch or unknown (no false negatives)."""
    try:
        with store.open_read(path) as reader:
            content = reader.read(max_bytes + 1)
        if len(content) > max_bytes:
            return "mismatch"
        return "match" if ByteIdentity.of(content) == expected else "mismatch"
    except FileNotFoundError:
        return "missing"
    except Exception:
        return "unknown"


class FileJournalWriter:
    """Stateless immutable-batch writer. Caller supplies the logical storage namespace."""
    def __init__(self, store: FileStore, root: str, *, writer_id: str,
                 policy: PersistencePolicy | None = None, max_segment_bytes: int = 8 * 1024 * 1024):
        if not root or "\x00" in root or not isinstance(root, str):
            raise ValueError("A caller-defined journal root is required")
        safe_token(writer_id)
        if max_segment_bytes < 4096:
            raise ValueError("Invalid segment byte limit")
        self.store, self.root, self.writer_id = store, root.rstrip("/\\"), writer_id
        self.policy = policy or PersistencePolicy()
        self.max_segment_bytes = max_segment_bytes

    def segment_path(self, segment_id: str) -> str:
        safe_token(segment_id)
        # Segment identifiers may only occupy one final filename component.
        return f"{self.root}/{self.writer_id}/{segment_id}.{self.policy.format}"

    def write_batch(self, records: Iterable[JournalRecord], *, segment_id: str | None = None) -> JournalWriteReceipt:
        batch_list: list[JournalRecord] = []
        measured = 2 if self.policy.format == "json" else 0
        # Bound generator consumption before materializing large external sequences.
        for record in records:
            from .codecs import encode_record
            measured += len(encode_record(record)) + 1
            if measured > self.max_segment_bytes:
                raise ValueError("Journal segment exceeds the maximum size")
            batch_list.append(record)
        batch = tuple(batch_list)
        if not batch:
            raise ValueError("Cannot persist an empty segment")
        data = encode_records(batch, format=self.policy.format)
        identity = ByteIdentity.of(data)
        ids = tuple(x.record_id for x in batch)
        segment_id = segment_id or sha256(
            (self.writer_id + ":" + identity.sha256 + ":" + ":".join(ids)).encode("utf-8")
        ).hexdigest()
        path = self.segment_path(segment_id)
        receipt = lambda state, diagnostic=None, already=False: JournalWriteReceipt(
            state, segment_id, identity, ids, "immutable_read_back", path, diagnostic, already)

        staged = callable(getattr(self.store, "stage_write", None))
        atomic = callable(getattr(self.store, "create_if_absent", None))
        if not staged and not atomic:
            return receipt("failed", "journal.immutable_capability_missing")
        # mkdir is neutral; callers should choose a controlled root.
        try:
            self.store.makedirs(f"{self.root}/{self.writer_id}")
        except Exception:
            return receipt("failed", "journal.destination_unavailable")
        attempted = False
        try:
            if staged:
                with self.store.stage_write(path) as stage:
                    stage.stream.write(data)
                    attempted = True
                    created = stage.commit("immutable", None)
            else:
                attempted = True
                created = self.store.create_if_absent(path, data)
        except Exception:
            # Once the commit call was entered, its outcome is not inferable.
            return receipt("unknown" if attempted else "failed",
                           "journal.commit_unknown" if attempted else "journal.staging_failed")
        match = _read_exact(self.store, path, identity, max_bytes=self.max_segment_bytes)
        if match == "match":
            return receipt("confirmed", already=not created)
        if match == "mismatch":
            return receipt("failed", "journal.segment_conflict" if not created else "journal.read_back_mismatch")
        return receipt("unknown", "journal.read_back_unavailable" if match == "unknown" else "journal.segment_missing")


def reconcile_write(store: FileStore, receipt: JournalWriteReceipt, *,
                    max_segment_bytes: int = 8 * 1024 * 1024) -> JournalWriteReceipt:
    result = _read_exact(store, receipt.locator, receipt.content_identity, max_bytes=max_segment_bytes)
    if result == "match":
        try:
            with store.open_read(receipt.locator) as stream:
                data = stream.read(max_segment_bytes + 1)
            records = decode_records(data, format="jsonl" if receipt.locator.endswith(".jsonl") else "json")
        except (JournalDecodeError, OSError, ValueError):
            result = "mismatch"
        else:
            if tuple(r.record_id for r in records) != receipt.record_ids:
                result = "mismatch"
    if result == "match":
        return JournalWriteReceipt("confirmed", receipt.segment_id, receipt.content_identity, receipt.record_ids,
                                   receipt.guarantee, receipt.locator, already_present=True)
    return JournalWriteReceipt("failed" if result == "mismatch" else "unknown", receipt.segment_id,
                               receipt.content_identity, receipt.record_ids, receipt.guarantee,
                               receipt.locator, "journal.segment_conflict" if result == "mismatch" else "journal.reconciliation_incomplete")


class FileJournalReader:
    def __init__(self, store: FileStore, *, max_segment_bytes: int = 8 * 1024 * 1024,
                 max_segments: int = 10000):
        if max_segment_bytes < 4096 or max_segments < 1:
            raise ValueError("Invalid journal read limits")
        self.store = store
        self.max_segment_bytes = max_segment_bytes
        self.max_segments = max_segments

    def iter_segments(self, paths: Iterable[str], *, expected: dict[str, ByteIdentity] | None = None) -> Iterator[JournalRecord]:
        count = 0
        for path in paths:
            count += 1
            if count > self.max_segments:
                raise JournalDecodeError("journal.segment_limit")
            with self.store.open_read(path) as stream:
                data = stream.read(self.max_segment_bytes + 1)
            if len(data) > self.max_segment_bytes:
                raise JournalDecodeError("journal.segment_too_large")
            if expected is not None and path in expected and ByteIdentity.of(data) != expected[path]:
                raise JournalDecodeError("journal.segment_identity_mismatch")
            if path.endswith(".jsonl"):
                yield from iter_decode_jsonl(data.splitlines(keepends=True))
            elif path.endswith(".json"):
                yield from decode_records(data, format="json")
            else:
                raise JournalDecodeError("journal.format_unknown")

    def read_report(self, paths: Iterable[str], *, expected: dict[str, ByteIdentity] | None = None,
                    expected_paths: frozenset[str] | None = None,
                    capture_complete: bool = False) -> JournalReadReport:
        paths = tuple(paths)
        if len(paths) > self.max_segments:
            raise ValueError("Too many requested segments")
        issues = [JournalReadIssue(path, "journal.expected_segment_missing")
                  for path in sorted((expected_paths or frozenset()) - set(paths))]
        records: list[JournalRecord] = []
        for path in paths:
            try:
                records.extend(self.iter_segments((path,), expected=expected))
            except FileNotFoundError:
                issues.append(JournalReadIssue(path, "journal.segment_missing"))
            except JournalDecodeError as exc:
                issues.append(JournalReadIssue(path, exc.code, exc.line))
            except Exception:
                issues.append(JournalReadIssue(path, "journal.segment_read_failed"))
        # Completeness must be positively asserted with an exact expected set.
        proven = bool(capture_complete and expected_paths is not None and
                      set(paths) == set(expected_paths) and not issues)
        return JournalReadReport(tuple(records), tuple(issues), proven)


class BufferedFileJournal:
    """Explicit bounded buffer; unflushed records are never claimed durable."""
    def __init__(self, writer: FileJournalWriter):
        self.writer = writer
        self._buffer: list[JournalRecord] = []
        self._size = 0
        self._receipts: list[JournalWriteReceipt] = []
        self._closed = False

    def append(self, record: JournalRecord) -> JournalWriteReceipt | None:
        if self._closed:
            raise RuntimeError("Journal is closed")
        size = len(encode_records((record,), format=self.writer.policy.format))
        if size > min(self.writer.policy.max_buffer_bytes, self.writer.max_segment_bytes):
            raise ValueError("One journal record exceeds buffer limit")
        emitted = None
        if self._buffer and (len(self._buffer) >= self.writer.policy.max_buffer_records or
                            self._size + size > self.writer.policy.max_buffer_bytes or
                            self._size + size > self.writer.max_segment_bytes):
            emitted = self.flush()
            if emitted is not None and emitted.state != "confirmed":
                raise JournalBarrierError(emitted)
        self._buffer.append(record)
        self._size += size
        if len(self._buffer) >= self.writer.policy.max_buffer_records:
            emitted = self.flush()
        return emitted

    def flush(self) -> JournalWriteReceipt | None:
        if not self._buffer:
            return None
        receipt = self.writer.write_batch(self._buffer)
        self._receipts.append(receipt)
        if receipt.state == "confirmed":
            self._buffer.clear()
            self._size = 0
        return receipt

    def close(self) -> tuple[JournalWriteReceipt, ...]:
        if self._closed:
            return tuple(self._receipts)
        last = self.flush()
        if last is not None and last.state != "confirmed":
            # Keep the buffered records available for explicit reconciliation/retry.
            return tuple(self._receipts)
        self._closed = True
        return tuple(self._receipts)

    @property
    def pending(self) -> tuple[JournalRecord, ...]:
        return tuple(self._buffer)


def require_confirmed(receipt: JournalWriteReceipt) -> JournalWriteReceipt:
    if receipt.state != "confirmed":
        raise JournalBarrierError(receipt)
    return receipt


class RequiredJournalGate:
    def __init__(self, writer: RecordWriter):
        self.writer = writer

    def require_confirmed(self, record: JournalRecord) -> JournalWriteReceipt:
        return require_confirmed(self.writer.write_batch((record,)))

    def execute_after_record(self, record: JournalRecord, action: Callable[[], object]) -> tuple[object, JournalWriteReceipt]:
        receipt = self.require_confirmed(record)
        return action(), receipt
