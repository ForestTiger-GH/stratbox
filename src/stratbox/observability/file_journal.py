"""Immutable file batches, scope-bound reconciliation and qualified recovery.

Read-back attests the same bytes at the time of observation. No independent
producer authenticity, fsync/power-loss promise or cross-segment transaction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from collections.abc import Callable, Iterable, Iterator, Mapping
from threading import RLock
from typing import Protocol

from stratbox.base.filestore import FileStore
from stratbox.data import ByteIdentity
from stratbox.execution.contracts import safe_token

from .codecs import (JournalDecodeError, decode_records, encode_record, encode_records,
                     DEFAULT_MAX_SEGMENT_BYTES)
from .contracts import JournalBarrierError, JournalRecord, JournalWriteReceipt
from .coverage import CaptureCoverage, GenerationCaptureAssessment
from .lifecycle import assess_generation_coverage, assess_invocation_lifecycle
from .manifests import (JournalManifest, MAX_MANIFEST_BYTES, SegmentDescriptor,
                        _ids_digest, decode_manifest, encode_manifest)
from .policies import PersistencePolicy


class RecordWriter(Protocol):
    def write_batch(self, records: Iterable[JournalRecord], *, segment_id: str | None = None) -> JournalWriteReceipt: ...


class RecordReader(Protocol):
    def iter_segments(self, paths: Iterable[str], *, expected: Mapping[str, ByteIdentity] | None = None) -> Iterator[JournalRecord]: ...


@dataclass(frozen=True, slots=True)
class JournalNamespace:
    root: str
    writer_id: str
    format: str = "jsonl"

    def __post_init__(self):
        safe_token(self.writer_id)
        if not isinstance(self.root, str) or not self.root or "\\" in self.root or "\x00" in self.root:
            raise ValueError("Invalid logical journal root")
        if self.root.startswith("/") or ":" in self.root or any(part in {"", ".", ".."} for part in self.root.split("/")):
            raise ValueError("Journal root must be a relative, scoped logical path")
        if self.format not in {"json", "jsonl"}:
            raise ValueError("Invalid journal format")

    def segment_path(self, segment_id: str) -> str:
        safe_token(segment_id)
        return f"{self.root}/{self.writer_id}/{segment_id}.{self.format}"

    def manifest_path(self, manifest_id: str) -> str:
        safe_token(manifest_id)
        return f"{self.root}/{self.writer_id}/{manifest_id}.manifest.json"

    def admits(self, path: str) -> bool:
        if not isinstance(path, str) or "\\" in path or "\x00" in path:
            return False
        prefix = f"{self.root}/{self.writer_id}/"
        if not path.startswith(prefix):
            return False
        name = path[len(prefix):]
        if "/" in name or not name.endswith("." + self.format):
            return False
        try:
            safe_token(name[:-(len(self.format) + 1)])
        except ValueError:
            return False
        return True


@dataclass(frozen=True, slots=True)
class JournalReadIssue:
    locator: str = field(repr=False)
    code: str = "journal.unknown"
    line: int | None = None


@dataclass(frozen=True, slots=True)
class JournalReadReport:
    records: tuple[JournalRecord, ...]
    issues: tuple[JournalReadIssue, ...]
    storage_coverage: str
    capture_coverage: str
    manifest_id: str | None = None

    @property
    def complete(self) -> bool:
        return self.storage_coverage == "complete" and self.capture_coverage == "complete"


def _read_bounded_segment(store: FileStore, path: str, max_bytes: int) -> tuple[bytes | None, str]:
    try:
        with store.open_read(path) as stream:
            data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None, "journal.segment_too_large"
        return data, "ok"
    except FileNotFoundError:
        return None, "journal.segment_missing"
    except Exception:
        return None, "journal.segment_read_failed"


def _check_segment(data: bytes, receipt: JournalWriteReceipt | None, format: str, *,
                   expected: ByteIdentity | None, max_bytes: int):
    if expected is not None and ByteIdentity.of(data) != expected:
        raise JournalDecodeError("journal.segment_identity_mismatch")
    records = decode_records(data, format=format, max_bytes=max_bytes)
    ids = tuple(rec.record_id for rec in records)
    if len(ids) != len(set(ids)):
        raise JournalDecodeError("journal.duplicate_record_id")
    if receipt is not None and (ids != receipt.record_ids or ByteIdentity.of(data) != receipt.content_identity):
        raise JournalDecodeError("journal.segment_content_conflict")
    return records


class FileJournalWriter:
    def __init__(self, store: FileStore, root: str, *, writer_id: str,
                 policy: PersistencePolicy | None = None,
                 max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES):
        if not 4096 <= max_segment_bytes <= 128 * 1024 * 1024:
            raise ValueError("Invalid maximum journal segment size")
        self.policy = policy or PersistencePolicy()
        self.namespace = JournalNamespace(root, writer_id, self.policy.format)
        self.store, self.max_segment_bytes = store, max_segment_bytes
        self.root, self.writer_id = self.namespace.root, self.namespace.writer_id

    def segment_path(self, segment_id: str) -> str:
        return self.namespace.segment_path(segment_id)

    def _publish(self, path: str, data: bytes) -> tuple[bool | None, str | None]:
        staged = callable(getattr(self.store, "stage_write", None))
        atomic = callable(getattr(self.store, "create_if_absent", None))
        if not (staged or atomic):
            return None, "journal.immutable_capability_missing"
        try:
            self.store.makedirs(f"{self.root}/{self.writer_id}")
        except Exception:
            return None, "journal.destination_unavailable"
        entered_commit = False
        try:
            if staged:
                with self.store.stage_write(path) as stage:
                    stage.stream.write(data)
                    entered_commit = True
                    created = stage.commit("immutable", None)
            else:
                entered_commit = True
                created = self.store.create_if_absent(path, data)
        except Exception:
            return None, "journal.commit_unknown" if entered_commit else "journal.staging_failed"
        return created, None

    def write_batch(self, records: Iterable[JournalRecord], *, segment_id: str | None = None) -> JournalWriteReceipt:
        data = encode_records(records, format=self.policy.format, max_bytes=self.max_segment_bytes)
        batch = _check_segment(data, None, self.policy.format, expected=None, max_bytes=self.max_segment_bytes)
        if not batch:
            raise ValueError("Cannot persist an empty journal segment")
        ids = tuple(rec.record_id for rec in batch)
        identity = ByteIdentity.of(data)
        chosen = segment_id or sha256((self.writer_id + ":" + identity.sha256 + ":" + ":".join(ids)).encode("utf-8")).hexdigest()
        path = self.segment_path(chosen)
        def receipt(state: str, error: str | None = None, already: bool = False) -> JournalWriteReceipt:
            return JournalWriteReceipt(state, chosen, identity, ids, "immutable_read_back", path, error, already)
        created, issue = self._publish(path, data)
        if issue and issue != "journal.commit_unknown":
            return receipt("failed", issue)
        if issue == "journal.commit_unknown":
            return receipt("unknown", issue)
        observed, reason = _read_bounded_segment(self.store, path, self.max_segment_bytes)
        if observed is None:
            return receipt("unknown", reason)
        if ByteIdentity.of(observed) != identity:
            return receipt("failed", "journal.segment_conflict" if not created else "journal.read_back_mismatch")
        return receipt("confirmed", already=not created)

    def reconcile(self, receipt: JournalWriteReceipt) -> JournalWriteReceipt:
        return reconcile_write(self.store, receipt, namespace=self.namespace,
                               max_segment_bytes=self.max_segment_bytes)

    def write_manifest(self, manifest: JournalManifest) -> JournalWriteReceipt:
        if manifest.writer_id != self.writer_id:
            raise ValueError("Manifest writer mismatch")
        if any(not self.namespace.admits(s.logical_locator) or self.segment_path(s.segment_id) != s.logical_locator
               for s in manifest.segments):
            raise ValueError("Manifest contains a segment outside the writer namespace")
        data = encode_manifest(manifest)
        identity = ByteIdentity.of(data)
        path = self.namespace.manifest_path(manifest.manifest_id)
        def receipt(state, code=None, already=False):
            return JournalWriteReceipt(state, manifest.manifest_id, identity, (),
                                       "immutable_read_back", path, code, already)
        created, issue = self._publish(path, data)
        if issue:
            return receipt("unknown" if issue == "journal.commit_unknown" else "failed", issue)
        observed, reason = _read_bounded_segment(self.store, path, MAX_MANIFEST_BYTES)
        if observed is None:
            return receipt("unknown", reason)
        return receipt("confirmed", already=not created) if ByteIdentity.of(observed) == identity else receipt("failed", "journal.manifest_conflict")


def reconcile_write(store: FileStore, receipt: JournalWriteReceipt, *, namespace: JournalNamespace,
                    max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES) -> JournalWriteReceipt:
    """One read, one identical byte buffer for digest + records + receipt IDs."""
    if not namespace.admits(receipt.locator) or namespace.segment_path(receipt.segment_id) != receipt.locator:
        raise ValueError("journal.namespace_mismatch")
    data, status = _read_bounded_segment(store, receipt.locator, max_segment_bytes)
    if data is None:
        if status == "journal.segment_too_large":
            state, code = "failed", status
        else:
            state, code = "unknown", "journal.reconciliation_incomplete"
    else:
        try:
            _check_segment(data, receipt, namespace.format, expected=receipt.content_identity,
                           max_bytes=max_segment_bytes)
        except JournalDecodeError:
            state, code = "failed", "journal.segment_conflict"
        else:
            state, code = "confirmed", None
    return JournalWriteReceipt(state, receipt.segment_id, receipt.content_identity, receipt.record_ids,
                               receipt.guarantee, receipt.locator, code,
                               already_present=state == "confirmed")


class FileJournalReader:
    def __init__(self, store: FileStore, *, namespace: JournalNamespace,
                 max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES,
                 max_segments: int = 10_000, max_records: int = 100_000,
                 max_total_bytes: int = 128 * 1024 * 1024):
        if not 4096 <= max_segment_bytes <= 128 * 1024 * 1024 or not 1 <= max_segments <= 100_000:
            raise ValueError("Invalid journal read limits")
        if not 1 <= max_records <= 1_000_000 or not 1 <= max_total_bytes <= 1024**3:
            raise ValueError("Invalid journal read budgets")
        self.store, self.namespace = store, namespace
        self.max_segment_bytes, self.max_segments = max_segment_bytes, max_segments
        self.max_records, self.max_total_bytes = max_records, max_total_bytes

    def _validated(self, path: str, *, expected: ByteIdentity | None = None,
                   descriptor: SegmentDescriptor | None = None) -> tuple[tuple[JournalRecord, ...], int]:
        if not self.namespace.admits(path):
            raise JournalDecodeError("journal.namespace_mismatch")
        content, issue = _read_bounded_segment(self.store, path, self.max_segment_bytes)
        if content is None:
            raise JournalDecodeError(issue)
        records = _check_segment(content, None, self.namespace.format, expected=expected,
                                 max_bytes=self.max_segment_bytes)
        if descriptor is not None:
            if (len(records) != descriptor.record_count or
                    _ids_digest(tuple(r.record_id for r in records)) != descriptor.record_ids_digest):
                raise JournalDecodeError("journal.segment_record_ids_mismatch")
        return records, len(content)

    def iter_segments(self, paths: Iterable[str], *, expected: Mapping[str, ByteIdentity] | None = None) -> Iterator[JournalRecord]:
        count = total_bytes = 0
        for n, path in enumerate(paths, 1):
            if n > self.max_segments:
                raise JournalDecodeError("journal.segment_limit")
            batch, size = self._validated(path, expected=expected.get(path) if expected else None)
            count += len(batch)
            total_bytes += size
            if count > self.max_records or total_bytes > self.max_total_bytes:
                raise JournalDecodeError("journal.report_budget_exceeded")
            yield from batch

    def load_manifest(self, receipt: JournalWriteReceipt) -> JournalManifest:
        if not receipt.locator.startswith(f"{self.namespace.root}/{self.namespace.writer_id}/") or receipt.locator != self.namespace.manifest_path(receipt.segment_id):
            raise JournalDecodeError("journal.namespace_mismatch")
        data, issue = _read_bounded_segment(self.store, receipt.locator, MAX_MANIFEST_BYTES)
        if data is None:
            raise JournalDecodeError(issue)
        if ByteIdentity.of(data) != receipt.content_identity:
            raise JournalDecodeError("journal.manifest_identity_mismatch")
        try:
            manifest = decode_manifest(data)
        except ValueError:
            raise JournalDecodeError("journal.manifest_invalid") from None
        if manifest.manifest_id != receipt.segment_id or manifest.writer_id != self.namespace.writer_id:
            raise JournalDecodeError("journal.manifest_identity_mismatch")
        return manifest

    def read_report(self, paths: Iterable[str] = (), *, expected: Mapping[str, ByteIdentity] | None = None,
                    manifest_receipt: JournalWriteReceipt | None = None) -> JournalReadReport:
        issues: list[JournalReadIssue] = []
        manifest: JournalManifest | None = None
        if manifest_receipt is not None:
            try:
                if manifest_receipt.state != "confirmed":
                    raise JournalDecodeError("journal.manifest_unconfirmed")
                manifest = self.load_manifest(manifest_receipt)
            except JournalDecodeError as error:
                issues.append(JournalReadIssue(manifest_receipt.locator, error.code, error.line))
        descriptors: dict[str, SegmentDescriptor] = {}
        if manifest is not None:
            for item in manifest.segments:
                if not self.namespace.admits(item.logical_locator) or self.namespace.segment_path(item.segment_id) != item.logical_locator:
                    issues.append(JournalReadIssue(item.logical_locator, "journal.namespace_mismatch"))
                descriptors[item.logical_locator] = item
            paths = tuple(descriptors)
        by_id: dict[str, JournalRecord] = {}
        conflicted: set[str] = set()
        seen_paths: set[str] = set()
        total_bytes = 0
        total_records = 0
        for n, path in enumerate(paths, 1):
            if n > self.max_segments:
                issues.append(JournalReadIssue("", "journal.segment_limit"))
                break
            if path in seen_paths:
                continue
            seen_paths.add(path)
            desc = descriptors.get(path)
            try:
                if desc is not None:
                    if desc.write_state != "confirmed":
                        raise JournalDecodeError("journal.segment_unconfirmed")
                batch, segment_bytes = self._validated(path, expected=desc.identity if desc else expected.get(path) if expected else None,
                                        descriptor=desc)
                if total_bytes + segment_bytes > self.max_total_bytes or total_records + len(batch) > self.max_records:
                    raise JournalDecodeError("journal.report_budget_exceeded")
                total_bytes += segment_bytes
                total_records += len(batch)
                for rec in batch:
                    old = by_id.get(rec.record_id)
                    if rec.record_id in conflicted:
                        continue
                    if old is not None and old != rec:
                        conflicted.add(rec.record_id)
                        issues.append(JournalReadIssue(path, "journal.record_identity_conflict"))
                    elif old is None:
                        by_id[rec.record_id] = rec
            except JournalDecodeError as error:
                issues.append(JournalReadIssue(path, error.code, error.line))
            except Exception:
                issues.append(JournalReadIssue(path, "journal.segment_read_failed"))
        for ident in conflicted:
            by_id.pop(ident, None)
        if manifest is not None:
            missing = set(descriptors) - seen_paths
            issues.extend(JournalReadIssue(path, "journal.expected_segment_missing") for path in sorted(missing))
        storage_status = "incomplete" if issues else "complete" if manifest is not None and manifest.seal_state == "sealed" else "indeterminate"
        capture_status = "indeterminate"
        if manifest is not None:
            # Aggregate every recovered invocation using a single indexed pass.
            # This assessment is independent of whether every physical segment
            # survived; storage coverage is calculated separately above.
            actual = assess_generation_coverage(by_id.values(), manifest.capture_evidence,
                                                scope_id=manifest.scope_id,
                                                generation_id=manifest.generation_id)
            capture_status = actual.status
            if actual != manifest.capture_assessment:
                capture_status = "incomplete"
                issues.append(JournalReadIssue("", "journal.generation_assessment_mismatch"))
            if manifest.seal_state != "sealed":
                capture_status = "incomplete" if capture_status == "complete" else capture_status
            if actual.status != "complete":
                issues.append(JournalReadIssue("", "journal.capture_evidence_inconsistent"))
            # A verified byte corpus cannot prove a complete producer stream
            # when missing or damaged segments hide entire invocations.
            if storage_status != "complete":
                capture_status = "incomplete" if capture_status == "complete" else capture_status
        return JournalReadReport(tuple(by_id.values()), tuple(issues), storage_status, capture_status,
                                 manifest.manifest_id if manifest else None)


class BufferedFileJournal:
    """Bounded pending buffer with explicit reconciliation of unknown commits."""
    def __init__(self, writer: FileJournalWriter, *, max_retained_receipts: int = 4096):
        if not 1 <= max_retained_receipts <= 100_000:
            raise ValueError("journal.receipt_limit_invalid")
        self.max_retained_receipts = max_retained_receipts
        self.writer = writer
        self._buffer: list[JournalRecord] = []
        self._bytes = 0
        self._receipts: dict[str, JournalWriteReceipt] = {}
        self._pending_receipt: JournalWriteReceipt | None = None
        self._closed = False
        self._lock = RLock()
        self._confirmed = self._failed = self._unknown = 0

    def _size_with(self, size: int) -> int:
        if self.writer.policy.format == "jsonl":
            return self._bytes + size + 1
        return (self._bytes if self._buffer else 2) + size + (1 if self._buffer else 0)

    def append(self, record: JournalRecord) -> JournalWriteReceipt | None:
        size = len(encode_record(record))
        with self._lock:
            if self._closed:
                raise RuntimeError("Journal is closed")
            if size + 2 > min(self.writer.policy.max_buffer_bytes, self.writer.max_segment_bytes):
                raise ValueError("journal.record_buffer_limit")
            result = None
            if self._buffer and (len(self._buffer) >= self.writer.policy.max_buffer_records or
                                 self._size_with(size) > self.writer.policy.max_buffer_bytes or
                                 self._size_with(size) > self.writer.max_segment_bytes):
                result = self.flush()
                if result is not None and result.state != "confirmed":
                    raise JournalBarrierError(result)
            self._bytes = self._size_with(size)
            self._buffer.append(record)
            if len(self._buffer) >= self.writer.policy.max_buffer_records:
                result = self.flush()
            return result

    def flush(self) -> JournalWriteReceipt | None:
        with self._lock:
            if not self._buffer:
                return None
            if self._pending_receipt is not None:
                return self._pending_receipt
            # Capacity is checked BEFORE publishing, so a successfully committed
            # segment can never be orphaned by an exhausted receipt catalogue.
            if len(self._receipts) >= self.max_retained_receipts:
                raise ValueError("journal.receipt_capacity_exceeded")
            receipt = self.writer.write_batch(tuple(self._buffer))
            self._receipts[receipt.segment_id] = receipt
            if receipt.state == "confirmed":
                self._confirmed += 1
                self._buffer.clear()
                self._bytes = 0
            else:
                self._pending_receipt = receipt
                if receipt.state == "unknown":
                    self._unknown += 1
                else:
                    self._failed += 1
            return receipt

    def reconcile_pending(self) -> JournalWriteReceipt | None:
        with self._lock:
            if self._pending_receipt is None:
                return None
            receipt = self.writer.reconcile(self._pending_receipt)
            self._receipts[receipt.segment_id] = receipt
            if receipt.state == "confirmed":
                self._confirmed += 1
                self._buffer.clear()
                self._bytes = 0
                self._pending_receipt = None
            else:
                self._pending_receipt = receipt
            return receipt

    def close(self) -> tuple[JournalWriteReceipt, ...]:
        with self._lock:
            if not self._closed and (self.flush() is None or self._pending_receipt is None):
                self._closed = True
            return tuple(self._receipts.values())

    @property
    def close_status(self) -> str:
        with self._lock:
            if self._pending_receipt is not None:
                return "pending_unconfirmed" if self._pending_receipt.state == "unknown" else "closed_failed"
            return "closed_confirmed" if self._closed else "open"

    @property
    def pending(self) -> tuple[JournalRecord, ...]:
        with self._lock:
            return tuple(self._buffer)

    @property
    def pending_bytes(self) -> int:
        with self._lock:
            return self._bytes

    @property
    def receipts(self) -> tuple[JournalWriteReceipt, ...]:
        with self._lock:
            return tuple(self._receipts.values())


    def snapshot_receipts(self) -> tuple[JournalWriteReceipt, ...]:
        """Bounded immutable handoff for a caller-controlled manifest or catalogue."""
        return self.receipts

    def acknowledge_receipts(self, segment_ids: Iterable[str]) -> int:
        """Only independently handled *confirmed* receipts may be released."""
        with self._lock:
            requested = tuple(segment_ids)
            if len(requested) > self.max_retained_receipts or len(set(requested)) != len(requested):
                raise ValueError("journal.receipt_ack_invalid")
            for segment_id in requested:
                receipt = self._receipts.get(segment_id)
                if receipt is None or receipt.state != "confirmed" or (
                    self._pending_receipt is not None and self._pending_receipt.segment_id == segment_id
                ):
                    raise ValueError("journal.receipt_ack_unconfirmed")
            for segment_id in requested:
                del self._receipts[segment_id]
            return len(requested)
    @property
    def flush_counts(self) -> tuple[int, int, int]:
        with self._lock:
            return self._confirmed, self._failed, self._unknown


def require_confirmed(receipt: JournalWriteReceipt) -> JournalWriteReceipt:
    if receipt.state != "confirmed":
        raise JournalBarrierError(receipt)
    return receipt


class RequiredJournalGate:
    """An explicit *pre-action* barrier; never a general EventSink policy."""
    def __init__(self, writer: RecordWriter):
        self.writer = writer

    def require_confirmed(self, record: JournalRecord) -> JournalWriteReceipt:
        return require_confirmed(self.writer.write_batch((record,)))

    def execute_after_record(self, record: JournalRecord, action: Callable[[], object]) -> tuple[object, JournalWriteReceipt]:
        receipt = self.require_confirmed(record)
        return action(), receipt
