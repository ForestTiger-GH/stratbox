"""Optional, bounded collectors; accepted-to-buffer never means stored-confirmed."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock

from stratbox.core.execution import ExecutionEvent, EventSink, OperationResult
from stratbox.core.execution.contracts import ObservabilitySummary
from stratbox.core.observability.capture.adapters import record_from_execution_event, record_from_fact, record_from_result
from stratbox.core.observability.records.contracts import DomainFact, JournalRecord, OriginClaim
from stratbox.core.observability.assessment.coverage import CaptureCoverage
from stratbox.core.observability.assessment.generation import ObserverGenerationSnapshot
from stratbox.core.observability.capture.tracking import _Counter
from stratbox.core.observability.capture.health import ObserverHealthSnapshot
from stratbox.core.observability.capture.policies import CapturePolicy, ObserverLimits
from stratbox.core.observability.journal.codecs import encode_record


@dataclass(frozen=True, slots=True)
class CaptureDisposition:
    state: str
    reason_code: str
    @property
    def accepted(self) -> bool:
        return self.state == "accepted"





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
