"""Bounded verified journal reads and read-only evidence assessment."""
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from stratbox.shared.identity import ByteIdentity
from stratbox.core.storage.filestore import FileStore
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.journal.contracts import JournalNamespace, JournalReadIssue, JournalReadReport, JournalWriteReceipt
from stratbox.core.observability.journal.codecs import JournalDecodeError, decode_records, DEFAULT_MAX_SEGMENT_BYTES, MAX_SEGMENT_BYTES
from stratbox.core.observability.journal.manifests import JournalManifest, SegmentDescriptor, MAX_MANIFEST_BYTES, _ids_digest, decode_manifest
from stratbox.core.observability.assessment.lifecycle import assess_generation_coverage

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

class FileJournalReader:
    def __init__(self, store: FileStore, *, namespace: JournalNamespace,
                 max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES,
                 max_segments: int = 10_000, max_records: int = 100_000,
                 max_total_bytes: int = 128 * 1024 * 1024):
        if not 4096 <= max_segment_bytes <= MAX_SEGMENT_BYTES or not 1 <= max_segments <= 100_000:
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

    def read_verified_segment(self, descriptor: SegmentDescriptor) -> tuple[JournalRecord, ...]:
        """Check the published descriptor and return records from the same bounded read."""
        if descriptor.logical_locator != self.namespace.segment_path(descriptor.segment_id):
            raise JournalDecodeError("journal.namespace_mismatch")
        if descriptor.write_state != "confirmed":
            raise JournalDecodeError("journal.segment_unconfirmed")
        if (descriptor.record_count > self.max_records
                or descriptor.identity.size > min(self.max_segment_bytes, self.max_total_bytes)):
            raise JournalDecodeError("journal.report_budget_exceeded")
        records, _ = self._validated(descriptor.logical_locator, expected=descriptor.identity,
                                     descriptor=descriptor)
        return records

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
