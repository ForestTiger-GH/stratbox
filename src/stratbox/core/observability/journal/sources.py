"""Bounded, positioned reads from a caller-bound observation source."""
from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

from stratbox.shared.data import ByteIdentity
from stratbox.core.execution.contracts import safe_token

from stratbox.core.observability.journal.codecs import JournalDecodeError, encode_record
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.assessment.coverage import CoverageStatus
from stratbox.core.observability.journal.file_reader import FileJournalReader
from stratbox.core.observability.journal.manifests import SegmentDescriptor
from stratbox.core.observability.assessment.generation import ObserverGenerationSnapshot

MAX_POSITION = 2**53 - 1
SourceProfile = Literal["local_snapshot", "resumable"]


def _offset(value: int, *, minimum: int = 0, maximum: int = MAX_POSITION) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("journal.position_invalid")


@dataclass(frozen=True, slots=True)
class StreamKey:
    scope_id: str
    stream_id: str
    partition_id: str

    def __post_init__(self) -> None:
        for value in (self.scope_id, self.stream_id, self.partition_id):
            safe_token(value)


@dataclass(frozen=True, slots=True)
class JournalCursor:
    stream: StreamKey
    epoch_id: str
    last_offset: int = 0
    cursor_version: int = 1

    def __post_init__(self) -> None:
        safe_token(self.epoch_id)
        _offset(self.last_offset)
        if type(self.cursor_version) is not int or self.cursor_version != 1:
            raise ValueError("journal.cursor_version_unsupported")


@dataclass(frozen=True, slots=True)
class JournalHead:
    stream: StreamKey
    epoch_id: str
    head_ref: str
    source_authority_id: str
    profile: SourceProfile
    first_retained: int
    tail_offset: int

    def __post_init__(self) -> None:
        for value in (self.epoch_id, self.head_ref, self.source_authority_id):
            safe_token(value)
        _offset(self.tail_offset)
        _offset(self.first_retained, minimum=1, maximum=self.tail_offset + 1)
        if self.profile not in {"local_snapshot", "resumable"}:
            raise ValueError("journal.source_profile_invalid")

    def cursor(self, last_offset: int) -> JournalCursor:
        return JournalCursor(self.stream, self.epoch_id, last_offset)

    def check(self, after: JournalCursor) -> None:
        if after.stream != self.stream:
            raise JournalDecodeError("journal.stream_mismatch")
        if after.epoch_id != self.epoch_id:
            raise JournalDecodeError("journal.epoch_mismatch")
        if after.last_offset < self.first_retained - 1:
            raise JournalDecodeError("journal.cursor_expired")
        if after.last_offset > self.tail_offset:
            raise JournalDecodeError("journal.cursor_ahead")


@dataclass(frozen=True, slots=True)
class JournalReadLimits:
    max_positions: int = 200
    max_bytes: int = 4 * 1024**2
    max_segments: int = 200
    max_io_bytes: int = 32 * 1024**2

    def __post_init__(self) -> None:
        for value, limit in ((self.max_positions, 10_000), (self.max_bytes, 128 * 1024**2),
                             (self.max_segments, 10_000), (self.max_io_bytes, 1024**3)):
            _offset(value, minimum=1, maximum=limit)


@dataclass(frozen=True, slots=True)
class JournalEntry:
    offset: int
    record: JournalRecord | None
    identity: ByteIdentity
    evidence_ref: str
    disposition: Literal["record", "duplicate", "technical"] = "record"

    def __post_init__(self) -> None:
        _offset(self.offset, minimum=1)
        safe_token(self.evidence_ref)
        if not isinstance(self.identity, ByteIdentity) or type(self.identity.size) is not int:
            raise ValueError("journal.entry_identity_invalid")
        if self.disposition not in {"record", "duplicate", "technical"}:
            raise ValueError("journal.entry_disposition_invalid")
        if (self.disposition == "record") != isinstance(self.record, JournalRecord):
            raise ValueError("journal.entry_record_invalid")

    @classmethod
    def from_record(cls, offset: int, record: JournalRecord, evidence_ref: str) -> JournalEntry:
        return cls(offset, record, ByteIdentity.of(encode_record(record)), evidence_ref)


@dataclass(frozen=True, slots=True)
class JournalReadProblem:
    first_offset: int
    last_offset: int
    code: str

    def __post_init__(self) -> None:
        _offset(self.first_offset, minimum=1)
        _offset(self.last_offset, minimum=self.first_offset)
        safe_token(self.code)


@dataclass(frozen=True, slots=True)
class JournalPage:
    head: JournalHead
    after: JournalCursor
    entries: tuple[JournalEntry, ...]
    problem: JournalReadProblem | None = None
    storage_coverage: CoverageStatus = "indeterminate"
    capture_coverage: CoverageStatus = "indeterminate"
    domain_coverage: Literal["complete", "incomplete", "indeterminate", "not_applicable"] = "indeterminate"

    @property
    def next_cursor(self) -> JournalCursor:
        return self.head.cursor(self.entries[-1].offset) if self.entries else self.after

    @property
    def has_more(self) -> bool:
        return self.next_cursor.last_offset < self.head.tail_offset

    def verify(self, after: JournalCursor, head: JournalHead, limits: JournalReadLimits) -> None:
        head.check(after)
        if self.head != head or self.after != after:
            raise JournalDecodeError("journal.page_snapshot_mismatch")
        if not isinstance(self.entries, tuple) or len(self.entries) > limits.max_positions:
            raise JournalDecodeError("journal.page_position_limit")
        for status in (self.storage_coverage, self.capture_coverage):
            if status not in {"complete", "incomplete", "indeterminate"}:
                raise JournalDecodeError("journal.page_coverage_invalid")
        if self.domain_coverage not in {"complete", "incomplete", "indeterminate", "not_applicable"}:
            raise JournalDecodeError("journal.page_coverage_invalid")
        size = 0
        expected = after.last_offset + 1
        for entry in self.entries:
            if entry.offset != expected or entry.offset > head.tail_offset:
                raise JournalDecodeError("journal.position_gap")
            size += entry.identity.size
            if size > limits.max_bytes:
                raise JournalDecodeError("journal.page_byte_limit")
            if entry.record is not None and ByteIdentity.of(encode_record(entry.record)) != entry.identity:
                raise JournalDecodeError("journal.record_identity_mismatch")
            expected += 1
        if self.problem is not None and (
            self.problem.first_offset != expected or self.problem.last_offset > head.tail_offset
        ):
            raise JournalDecodeError("journal.problem_position_invalid")
        if self.has_more and not self.entries and self.problem is None:
            raise JournalDecodeError("journal.position_gap")


class JournalSource(Protocol):
    def head(self, stream: StreamKey) -> JournalHead: ...

    def read_page(
        self, after: JournalCursor, *, head: JournalHead, limits: JournalReadLimits
    ) -> JournalPage: ...


class EpochJournalSource(JournalSource, Protocol):
    """An optional source capability for reading a retained journal epoch."""

    def head_for_epoch(self, stream: StreamKey, epoch_id: str) -> JournalHead:
        """Return a head accepted by read_page or raise a qualified read error."""
        ...


def _page(
    after: JournalCursor, head: JournalHead, limits: JournalReadLimits,
    records: Iterable[JournalEntry | JournalReadProblem], *,
    storage: CoverageStatus, capture: CoverageStatus,
) -> JournalPage:
    entries: list[JournalEntry] = []
    problem = None
    used = 0
    identities: dict[str, ByteIdentity] = {}
    for item in records:
        if isinstance(item, JournalReadProblem):
            problem = item
            break
        used += item.identity.size
        if used > limits.max_bytes:
            if not entries:
                problem = JournalReadProblem(item.offset, item.offset, "journal.page_entry_too_large")
            break
        if item.record is not None:
            previous = identities.setdefault(item.record.record_id, item.identity)
            if previous != item.identity:
                problem = JournalReadProblem(item.offset, item.offset, "journal.record_identity_conflict")
                break
        entries.append(item)
        if len(entries) == limits.max_positions:
            break
    return JournalPage(head, after, tuple(entries), problem, "incomplete" if problem else storage, capture)


class SnapshotJournalSource:
    """A closed collector generation with process-local positions."""

    def __init__(
        self, snapshot: ObserverGenerationSnapshot, stream: StreamKey, *,
        source_authority_id: str, epoch_id: str,
    ):
        if not snapshot.health.generation_finalized:
            raise ValueError("journal.snapshot_open")
        if snapshot.generation_id is not None and snapshot.generation_id != epoch_id:
            raise ValueError("journal.snapshot_epoch_mismatch")
        self._entries = tuple(JournalEntry.from_record(i, record, epoch_id)
                              for i, record in enumerate(snapshot.records, 1))
        self._head = JournalHead(stream, epoch_id, epoch_id, source_authority_id,
                                 "local_snapshot", 1, len(self._entries))
        self._capture: CoverageStatus = "incomplete" if snapshot.health.degraded else "indeterminate"

    def head(self, stream: StreamKey) -> JournalHead:
        if stream != self._head.stream:
            raise JournalDecodeError("journal.stream_mismatch")
        return self._head

    def read_page(self, after: JournalCursor, *, head: JournalHead, limits: JournalReadLimits) -> JournalPage:
        if head != self.head(after.stream):
            raise JournalDecodeError("journal.page_snapshot_mismatch")
        head.check(after)
        end = min(head.tail_offset, after.last_offset + limits.max_positions)
        return _page(after, head, limits, self._entries[after.last_offset:end],
                     storage="indeterminate", capture=self._capture)


@dataclass(frozen=True, slots=True)
class IndexedSegment:
    first_offset: int
    descriptor: SegmentDescriptor

    def __post_init__(self) -> None:
        _offset(self.first_offset, minimum=1)
        _offset(self.descriptor.record_count, minimum=1)
        _offset(self.last_offset, minimum=self.first_offset)

    @property
    def last_offset(self) -> int:
        return self.first_offset + self.descriptor.record_count - 1


class FileJournalSource:
    """Read a pinned publication index supplied by the owner of the journal."""

    def __init__(
        self, reader: FileJournalReader, head: JournalHead, segments: Iterable[IndexedSegment], *,
        capture_coverage: CoverageStatus = "indeterminate",
    ):
        if head.profile != "resumable":
            raise ValueError("journal.source_profile_invalid")
        index: list[IndexedSegment] = []
        paths: set[str] = set()
        previous_end = head.first_retained - 1
        for item in segments:
            path = item.descriptor.logical_locator
            if (
                len(index) == reader.max_segments or item.first_offset <= previous_end
                or item.last_offset > head.tail_offset or path in paths
            ):
                raise ValueError("journal.index_invalid")
            paths.add(path)
            index.append(item)
            previous_end = item.last_offset
        self._reader = reader
        self._head = head
        self._index = tuple(index)
        self._starts = tuple(s.first_offset for s in index)
        self._capture = capture_coverage

    def head(self, stream: StreamKey) -> JournalHead:
        if stream != self._head.stream:
            raise JournalDecodeError("journal.stream_mismatch")
        return self._head

    def read_page(self, after: JournalCursor, *, head: JournalHead, limits: JournalReadLimits) -> JournalPage:
        if head != self.head(after.stream):
            raise JournalDecodeError("journal.page_snapshot_mismatch")
        head.check(after)
        return _page(after, head, limits, self._records(after.last_offset + 1, limits),
                     storage="complete", capture=self._capture)

    def _records(self, offset: int, limits: JournalReadLimits) -> Iterable[JournalEntry | JournalReadProblem]:
        i = max(0, bisect_right(self._starts, offset) - 1)
        used = read_segments = 0
        while offset <= self._head.tail_offset:
            if i == len(self._index) or self._index[i].first_offset > offset:
                end = self._index[i].first_offset - 1 if i < len(self._index) else self._head.tail_offset
                yield JournalReadProblem(offset, end, "journal.position_gap")
                return
            item = self._index[i]
            i += 1
            if offset > item.last_offset:
                continue
            size = item.descriptor.identity.size
            if read_segments == limits.max_segments or used + size > limits.max_io_bytes:
                if not read_segments:
                    yield JournalReadProblem(offset, item.last_offset, "journal.segment_io_limit")
                return
            try:
                records = self._reader.read_verified_segment(item.descriptor)
            except JournalDecodeError as error:
                yield JournalReadProblem(offset, item.last_offset, error.code)
                return
            used += size
            read_segments += 1
            for record in records[offset - item.first_offset:]:
                yield JournalEntry.from_record(offset, record, item.descriptor.segment_id)
                offset += 1
