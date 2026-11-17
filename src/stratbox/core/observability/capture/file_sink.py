"""Optional best-effort capture sink with bounded journal storage."""
from __future__ import annotations
from threading import RLock
from stratbox.core.execution import ExecutionEvent
from stratbox.core.execution.contracts import ObservabilitySummary
from stratbox.core.observability.records.contracts import JournalRecord, OriginClaim
from stratbox.core.observability.capture.adapters import record_from_execution_event
from stratbox.core.observability.capture.policies import CapturePolicy, ObserverLimits
from stratbox.core.observability.capture.health import ObserverHealthSnapshot
from stratbox.core.observability.capture.sinks import CaptureDisposition
from stratbox.core.observability.capture.tracking import _Counter
from stratbox.core.observability.assessment.generation import ObserverGenerationSnapshot
from stratbox.core.observability.assessment.coverage import CaptureCoverage

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
