"""Optional, bounded collectors; accepted-to-buffer never means stored-confirmed."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock

from stratbox.execution import ExecutionEvent, EventSink, OperationResult
from stratbox.execution.contracts import ObservabilitySummary
from .adapters import record_from_execution_event, record_from_fact, record_from_result
from .contracts import DomainFact, JournalRecord, OriginClaim
from .coverage import CaptureCoverage, SequenceRange, merge_ranges
from .health import ObserverHealthSnapshot
from .policies import CapturePolicy
from .codecs import encode_record


@dataclass(frozen=True, slots=True)
class CaptureDisposition:
    state: str
    reason_code: str
    @property
    def accepted(self) -> bool:
        return self.state == "accepted"


class _Counter:
    def __init__(self):
        self.received = self.accepted = self.filtered = self.dropped_capacity = self.failed = 0
        self._seen: dict[str, list[SequenceRange]] = {}
        self._excluded: dict[str, list[SequenceRange]] = {}
        self._lost: dict[str, list[SequenceRange]] = {}
        self._start: set[str] = set()
        self._terminal: set[str] = set()
        self._overflowed: set[str] = set()

    @staticmethod
    def _put(table: dict[str, list[SequenceRange]], invocation: str, seq: int, overflow: set[str]):
        if invocation in overflow:
            return
        ranges = table.setdefault(invocation, [])
        if ranges and seq == ranges[-1].last + 1:
            ranges[-1] = SequenceRange(ranges[-1].first, seq)
        elif ranges and ranges[-1].first <= seq <= ranges[-1].last:
            return
        elif ranges and seq < ranges[-1].first:
            ranges[:] = merge_ranges((*ranges, SequenceRange(seq, seq)))
        else:
            if len(ranges) >= 50_000:
                overflow.add(invocation)
                return
            ranges.append(SequenceRange(seq, seq))

    def seen(self, rec: JournalRecord):
        if rec.record_type == "execution" and rec.invocation_id and rec.sequence:
            self._put(self._seen, rec.invocation_id, rec.sequence, self._overflowed)
            if rec.kind == "operation.started":
                self._start.add(rec.invocation_id)
            if rec.kind == "operation.finished":
                self._terminal.add(rec.invocation_id)

    def note_filtered(self, rec: JournalRecord):
        if rec.record_type == "execution" and rec.invocation_id and rec.sequence:
            self._put(self._excluded, rec.invocation_id, rec.sequence, self._overflowed)

    def lost(self, rec: JournalRecord):
        if rec.record_type == "execution" and rec.invocation_id and rec.sequence:
            self._put(self._lost, rec.invocation_id, rec.sequence, self._overflowed)

    def coverage(self, invocation: str, *, producer: ObservabilitySummary | None,
                 scope_id: str, generation_id: str | None = None) -> CaptureCoverage:
        seen = tuple(self._seen.get(invocation, ()))
        last = producer.emitted + producer.dropped if producer else None
        return CaptureCoverage(invocation, scope_id, last, seen,
                               tuple(self._excluded.get(invocation, ())),
                               tuple(self._lost.get(invocation, ())),
                               1 if invocation in self._overflowed else 0,
                               producer.dropped if producer else None,
                               invocation in self._terminal, generation_id,
                               "collector_observed" if producer is not None and seen and invocation not in self._overflowed else "claimed",
                               invocation in self._start)


class RecordMemorySink:
    def __init__(self, policy: CapturePolicy | None = None, *, origin: OriginClaim | None = None):
        self.policy = policy or CapturePolicy()
        self.origin = origin
        self._records: list[JournalRecord] = []
        self._bytes_used = 0
        self._counter = _Counter()
        self._lock = RLock()

    def capture_disposition(self, rec: JournalRecord) -> CaptureDisposition:
        with self._lock:
            c = self._counter
            c.received += 1
            c.seen(rec)
            reason = self.policy.classify(rec)
            if reason != "accepted":
                c.filtered += 1
                c.filtered_record = reason
                c.note_filtered(rec)
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
        self.capture(record_from_execution_event(event))

    def capture_fact(self, fact: DomainFact, *, operation_id: str | None = None,
                     invocation_id: str | None = None) -> bool:
        return self.capture(record_from_fact(fact, operation_id=operation_id, invocation_id=invocation_id))

    def capture_result(self, result: OperationResult, **kwargs) -> bool:
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
                                          degraded=bool(c.dropped_capacity + c.failed + (producer.dropped if producer else 0)))

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
    def __init__(self, journal, policy: CapturePolicy | None = None):
        self.journal = journal
        self.policy = policy or CapturePolicy()
        self._lock = RLock()
        self._counter = _Counter()

    def capture_disposition(self, record: JournalRecord) -> CaptureDisposition:
        with self._lock:
            c = self._counter
            c.received += 1
            c.seen(record)
            choice = self.policy.classify(record)
            if choice != "accepted":
                c.filtered += 1
                c.note_filtered(record)
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
            return self.journal.close()

    def coverage_for(self, invocation_id: str, *, producer: ObservabilitySummary | None = None) -> CaptureCoverage:
        policy_scope = "lifecycle_without_progress" if (not self.policy.progress and self.policy.kinds is None and self.policy.record_types is None) else "custom_capture"
        with self._lock:
            return self._counter.coverage(invocation_id, producer=producer, scope_id=policy_scope)

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
                                          degraded=bool(c.failed + failed + unknown + pending + (producer.dropped if producer else 0)))

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._counter.failed
