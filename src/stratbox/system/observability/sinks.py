"""Optional, bounded collectors; accepted-to-buffer never means stored-confirmed."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock

from stratbox.system.execution import ExecutionEvent, EventSink, OperationResult
from stratbox.system.execution.contracts import ObservabilitySummary
from .adapters import record_from_execution_event, record_from_fact, record_from_result
from .contracts import DomainFact, JournalRecord, OriginClaim
from .coverage import CaptureCoverage, SequenceRange, merge_ranges
from .health import ObserverHealthSnapshot
from .policies import CapturePolicy, ObserverLimits
from .codecs import encode_record


@dataclass(frozen=True, slots=True)
class CaptureDisposition:
    state: str
    reason_code: str
    @property
    def accepted(self) -> bool:
        return self.state == "accepted"


@dataclass(slots=True)
class _InvocationTracker:
    seen: list[SequenceRange]
    excluded: list[SequenceRange]
    lost: list[SequenceRange]
    start_seen: bool = False
    terminal_seen: bool = False
    overflowed: bool = False


@dataclass(frozen=True, slots=True)
class ObserverGenerationSnapshot:
    records: tuple[JournalRecord, ...]
    health: ObserverHealthSnapshot
    invocation_ids: tuple[str, ...]
    generation_id: str | None
    # An in-memory snapshot is volatile, never automatically storage-confirmed.


class _Counter:
    def __init__(self, limits: ObserverLimits):
        self.limits = limits
        self.received = self.accepted = self.filtered = self.dropped_capacity = self.failed = 0
        self.metadata_overflow = 0
        self._invocations: dict[str, _InvocationTracker] = {}
        self._total_ranges = 0

    @property
    def tracked_ranges(self) -> int:
        return self._total_ranges

    @staticmethod
    def _merged_count(items: list[SequenceRange], seq: int) -> tuple[SequenceRange, ...]:
        # Existing intervals are bounded; duplicates and adjacent sequences cost no new slot.
        return merge_ranges((*items, SequenceRange(seq, seq)))

    def observe(self, rec: JournalRecord, *, filtered: bool = False) -> bool:
        if rec.record_type != "execution" or not rec.invocation_id or rec.sequence is None:
            return True
        key = rec.invocation_id
        tracker = self._invocations.get(key)
        if tracker is None:
            if len(self._invocations) >= self.limits.max_tracked_invocations:
                self.metadata_overflow += 1
                return False
            tracker = _InvocationTracker([], [], [])
            self._invocations[key] = tracker
        if tracker.overflowed:
            self.metadata_overflow += 1
            return False
        seen = self._merged_count(tracker.seen, rec.sequence)
        excluded = self._merged_count(tracker.excluded, rec.sequence) if filtered else tuple(tracker.excluded)
        old_count = len(tracker.seen) + len(tracker.excluded) + len(tracker.lost)
        new_count = len(seen) + len(excluded) + len(tracker.lost)
        if new_count > self.limits.max_ranges_per_invocation or (self._total_ranges - old_count + new_count) > self.limits.max_total_sequence_ranges:
            tracker.overflowed = True
            self.metadata_overflow += 1
            return False
        self._total_ranges += new_count - old_count
        tracker.seen = list(seen)
        tracker.excluded = list(excluded)
        tracker.start_seen |= rec.kind == "operation.started"
        tracker.terminal_seen |= rec.kind == "operation.finished"
        return True

    def lost(self, rec: JournalRecord) -> None:
        if rec.record_type != "execution" or not rec.invocation_id or rec.sequence is None:
            return
        tracker = self._invocations.get(rec.invocation_id)
        if tracker is None or tracker.overflowed:
            return
        updated = self._merged_count(tracker.lost, rec.sequence)
        growth = len(updated) - len(tracker.lost)
        if (len(tracker.seen) + len(tracker.excluded) + len(updated) > self.limits.max_ranges_per_invocation
                or self._total_ranges + growth > self.limits.max_total_sequence_ranges):
            tracker.overflowed = True
            self.metadata_overflow += 1
            return
        self._total_ranges += growth
        tracker.lost = list(updated)

    def coverage(self, invocation: str, *, producer: ObservabilitySummary | None,
                 scope_id: str, generation_id: str | None = None) -> CaptureCoverage:
        tracker = self._invocations.get(invocation)
        seen = tuple(tracker.seen) if tracker else ()
        last = producer.emitted + producer.dropped if producer else None
        unknown = int(tracker.overflowed) if tracker else (1 if self.metadata_overflow else 0)
        return CaptureCoverage(invocation, scope_id, last, seen,
                               tuple(tracker.excluded) if tracker else (),
                               tuple(tracker.lost) if tracker else (), unknown,
                               producer.dropped if producer else None,
                               tracker.terminal_seen if tracker else False, generation_id,
                               "collector_observed" if producer is not None and seen and not unknown else "claimed",
                               tracker.start_seen if tracker else False)


class RecordMemorySink:
    def __init__(self, policy: CapturePolicy | None = None, *, origin: OriginClaim | None = None,
                 limits: ObserverLimits | None = None):
        self.policy = policy or CapturePolicy()
        self.origin = origin
        self._records: list[JournalRecord] = []
        self._finished: dict[str, ExecutionEvent | None] = {}
        self._bytes_used = 0
        self._counter = _Counter(limits or ObserverLimits())
        self._closed = False
        self._lock = RLock()

    def capture_disposition(self, rec: JournalRecord) -> CaptureDisposition:
        with self._lock:
            c = self._counter
            c.received += 1
            if self._closed:
                c.failed += 1
                return CaptureDisposition("failed", "journal.generation_closed")
            reason = self.policy.classify(rec)
            if not c.observe(rec, filtered=reason != "accepted"):
                c.dropped_capacity += 1
                return CaptureDisposition("dropped", "journal.coverage_metadata_limit")
            if reason != "accepted":
                c.filtered += 1
                return CaptureDisposition("filtered", reason)
            try:
                size = len(encode_record(rec))
            except (ValueError, TypeError):
                c.failed += 1
                c.lost(rec)
                return CaptureDisposition("failed", "journal.encoding_failed")
            if len(self._records) >= self.policy.max_records or self._bytes_used + size > self.policy.max_bytes:
                c.dropped_capacity += 1
                c.lost(rec)
                return CaptureDisposition("dropped", "journal.capture_limit")
            self._records.append(rec)
            self._bytes_used += size
            c.accepted += 1
            return CaptureDisposition("accepted", "journal.accepted_in_memory")

    def capture(self, record: JournalRecord) -> bool:
        return self.capture_disposition(record).accepted

    def emit(self, event: ExecutionEvent) -> None:
        with self._lock:
            accepted = self.capture(record_from_execution_event(event))
            if accepted and event.kind == "operation.finished":
                previous = self._finished.setdefault(event.invocation_id, event)
                if previous != event:
                    self._finished[event.invocation_id] = None

    def finished_event(self, invocation_id: str) -> ExecutionEvent | None:
        with self._lock:
            return self._finished.get(invocation_id)

    def capture_fact(self, fact: DomainFact, *, operation_id: str | None = None,
                     invocation_id: str | None = None) -> bool:
        return self.capture(record_from_fact(fact, operation_id=operation_id, invocation_id=invocation_id))

    def capture_result(self, result: OperationResult, **kwargs) -> bool:
        if "finished_event" not in kwargs and not {"occurred_at_utc", "observation_id"} & kwargs.keys():
            kwargs["finished_event"] = self.finished_event(result.invocation_id)
        return self.capture(record_from_result(result, **kwargs))

    def coverage_for(self, invocation_id: str, *, producer: ObservabilitySummary | None = None) -> CaptureCoverage:
        policy_scope = "lifecycle_without_progress" if (not self.policy.progress and self.policy.kinds is None and self.policy.record_types is None) else "custom_capture"
        with self._lock:
            return self._counter.coverage(invocation_id, producer=producer, scope_id=policy_scope,
                                          generation_id=self.origin.generation_id if self.origin else None)

    def health_snapshot(self, *, producer: ObservabilitySummary | None = None) -> ObserverHealthSnapshot:
        with self._lock:
            c = self._counter
            return ObserverHealthSnapshot(producer.emitted if producer else None,
                                          producer.dropped if producer else None, c.received,
                                          c.accepted, c.filtered, c.dropped_capacity + c.failed,
                                          degraded=bool(c.dropped_capacity + c.failed + c.metadata_overflow + (producer.dropped if producer else 0)),
                                          tracked_invocations=len(c._invocations), tracked_sequence_ranges=c.tracked_ranges,
                                          metadata_overflow_events=c.metadata_overflow, generation_finalized=self._closed)

    @property
    def records(self) -> tuple[JournalRecord, ...]:
        with self._lock:
            return tuple(self._records)

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._counter.dropped_capacity + self._counter.failed

    @property
    def policy_filtered(self) -> int:
        with self._lock:
            return self._counter.filtered

    @property
    def bytes_used(self) -> int:
        with self._lock:
            return self._bytes_used

    def finalize_generation(self) -> ObserverGenerationSnapshot:
        with self._lock:
            self._closed = True
            return ObserverGenerationSnapshot(self.records, self.health_snapshot(),
                tuple(sorted(self._counter._invocations)),
                self.origin.generation_id if self.origin else None)


class CompositeEventSink:
    def __init__(self, *sinks: EventSink):
        self.sinks = tuple(sinks)
        self._lock = RLock()
        self._failures = [0] * len(sinks)

    def emit(self, event: ExecutionEvent) -> None:
        for n, sink in enumerate(self.sinks):
            try:
                sink.emit(event)
            except Exception:
                with self._lock:
                    self._failures[n] += 1

    @property
    def dropped(self) -> int:
        with self._lock:
            return sum(self._failures)

    @property
    def recipient_failures(self) -> tuple[int, ...]:
        with self._lock:
            return tuple(self._failures)


class FileEventSink:
    """Best-effort sink; append acceptance is not storage confirmation."""
    def __init__(self, journal, policy: CapturePolicy | None = None, *,
                 origin: OriginClaim | None = None, limits: ObserverLimits | None = None):
        self.journal = journal
        self.policy = policy or CapturePolicy()
        self.origin = origin
        self._lock = RLock()
        self._counter = _Counter(limits or ObserverLimits())
        self._closed = False

    def capture_disposition(self, record: JournalRecord) -> CaptureDisposition:
        with self._lock:
            c = self._counter
            c.received += 1
            if self._closed:
                c.failed += 1
                return CaptureDisposition("failed", "journal.generation_closed")
            choice = self.policy.classify(record)
            if not c.observe(record, filtered=choice != "accepted"):
                c.dropped_capacity += 1
                return CaptureDisposition("dropped", "journal.coverage_metadata_limit")
            if choice != "accepted":
                c.filtered += 1
                return CaptureDisposition("filtered", choice)
            try:
                receipt = self.journal.append(record)
                if receipt is not None and receipt.state != "confirmed":
                    c.failed += 1
                    c.lost(record)
                    return CaptureDisposition("unknown" if receipt.state == "unknown" else "failed", "journal.flush_unconfirmed")
            except Exception:
                c.failed += 1
                c.lost(record)
                return CaptureDisposition("failed", "journal.append_failed")
            c.accepted += 1
            return CaptureDisposition("accepted", "journal.accepted_to_buffer")

    def capture(self, record: JournalRecord) -> bool:
        return self.capture_disposition(record).accepted

    def emit(self, event: ExecutionEvent) -> None:
        self.capture(record_from_execution_event(event))

    def flush(self):
        with self._lock:
            return self.journal.flush()

    def close(self):
        with self._lock:
            self._closed = True
            return self.journal.close()

    def finalize_generation(self) -> ObserverGenerationSnapshot:
        with self._lock:
            self.close()
            return ObserverGenerationSnapshot((), self.health_snapshot(),
                tuple(sorted(self._counter._invocations)),
                self.origin.generation_id if self.origin else None)

    def coverage_for(self, invocation_id: str, *, producer: ObservabilitySummary | None = None) -> CaptureCoverage:
        policy_scope = "lifecycle_without_progress" if (not self.policy.progress and self.policy.kinds is None and self.policy.record_types is None) else "custom_capture"
        with self._lock:
            return self._counter.coverage(invocation_id, producer=producer, scope_id=policy_scope,
                                          generation_id=self.origin.generation_id if self.origin else None)

    def health_snapshot(self, *, producer: ObservabilitySummary | None = None) -> ObserverHealthSnapshot:
        with self._lock:
            c = self._counter
            confirmed, failed, unknown = self.journal.flush_counts
            pending = len(self.journal.pending)
            return ObserverHealthSnapshot(producer.emitted if producer else None,
                                          producer.dropped if producer else None,
                                          c.received, c.accepted, c.filtered,
                                          c.dropped_capacity + c.failed, pending,
                                          self.journal.pending_bytes, confirmed, failed, unknown,
                                          degraded=bool(c.failed + c.dropped_capacity + c.metadata_overflow + failed + unknown + pending + (producer.dropped if producer else 0)),
                                          tracked_invocations=len(c._invocations), tracked_sequence_ranges=c.tracked_ranges,
                                          metadata_overflow_events=c.metadata_overflow,
                                          retained_receipts=len(self.journal.receipts), generation_finalized=self._closed)

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._counter.failed + self._counter.dropped_capacity
