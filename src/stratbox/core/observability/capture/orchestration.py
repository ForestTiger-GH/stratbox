"""Bounded scheduler telemetry and retained notification transitions."""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from queue import Empty, Full, Queue
from threading import Event, RLock, Thread

from stratbox.core.execution.contracts import Correlation
from stratbox.core.execution.events import ExecutionEvent
from stratbox.core.observability.capture.adapters import record_from_execution_event
from stratbox.core.observability.journal.codecs import encode_record
from stratbox.core.observability.journal.live import LiveJournalSource
from stratbox.core.observability.journal.sources import StreamKey
from stratbox.core.observability.records.field_policy import validate_builtin_fields
from stratbox.core.observability.records.orchestration import OrchestrationEvent, record_from_orchestration_event


@dataclass(frozen=True, slots=True)
class OrchestrationHealth:
    emitted: int
    retained: int
    evicted: int
    observer_dropped: int
    observer_failed: int
    pending_transitions: int
    reserved_transitions: int
    coverage: str
    unpublished_transitions: int
    publication_failures: int


@dataclass(frozen=True, slots=True)
class _OperationSink:
    journal: object
    target: object

    def emit(self, event: ExecutionEvent) -> None:
        self.journal.emit(event)
        self.journal.forward_event(event, self.target)


class OrchestrationJournal:
    """One local capture owner; callbacks never execute on the coordinator.

    ``source`` holds terminal transition evidence, while ``records`` is a bounded
    diagnostic view. Notification prepare/deliver use the existing runtime with
    this source. No consumer or external delivery is started implicitly.
    """

    def __init__(self, session_id: str, *, max_records: int = 4096,
                 max_bytes: int = 8 * 1024**2, max_pending_runs: int = 4096,
                 telemetry_sink=None, observer_queue_size: int = 256):
        if type(max_records) is not int or max_records < 1 or type(max_bytes) is not int or max_bytes < 8192:
            raise ValueError("orchestration.capture_limit_invalid")
        if type(observer_queue_size) is not int or observer_queue_size < 1:
            raise ValueError("orchestration.observer_limit_invalid")
        self.session_id = session_id
        self.stream = StreamKey(session_id, "execution", "runs")
        self.source = LiveJournalSource(self.stream, epoch_id=session_id,
                                       source_authority_id="execution.session",
                                       max_records=max_pending_runs,
                                       max_bytes=max_pending_runs * 8192)
        self.facts_stream = StreamKey(session_id, "execution", "accepted")
        self.facts_source = LiveJournalSource(self.facts_stream, epoch_id=session_id,
                                             source_authority_id="execution.acceptance",
                                             max_records=max_pending_runs,
                                             max_bytes=max_pending_runs * 8192)
        self._max_records, self._max_bytes = max_records, max_bytes
        self._records = deque()
        self._finished_events = OrderedDict()
        self._bytes = self._sequence = self._emitted = self._evicted = 0
        self._observer_dropped = self._observer_failed = 0
        self._observer_bytes = 0
        self._pending_transitions = {}
        self._publication_failures = 0
        self._sink = telemetry_sink
        self._queue = Queue(maxsize=observer_queue_size)
        self._stop = Event()
        self._lock = RLock()
        self._thread = None
        if telemetry_sink is not None:
            self._thread = Thread(target=self._observe, name="stratbox-observer", daemon=True)
            self._thread.start()

    def operation_sink(self, existing_sink=None):
        """Retain a caller's operation sink through the bounded observer queue.

        The caller still owns that sink and its lifetime. A sink supplied for
        one run receives only that run's raw operation events, while the session
        observer continues receiving qualified JournalRecord projections.
        """
        if existing_sink is None or existing_sink is self:
            return self
        if isinstance(existing_sink, _OperationSink) and existing_sink.journal is self:
            return existing_sink
        if existing_sink is self._sink and hasattr(existing_sink, "capture"):
            return self
        return _OperationSink(self, existing_sink)

    def forward_event(self, event: ExecutionEvent, target) -> None:
        if target is self or isinstance(target, _OperationSink) and target.journal is self:
            return
        self._enqueue_observation(event, target, "event", len(event.to_json().encode("utf-8")))

    def _enqueue_observation(self, value, target, mode, encoded_size):
        with self._lock:
            if self._stop.is_set() or self._observer_bytes + encoded_size > self._max_bytes:
                self._observer_dropped += 1
                return
            try:
                self._queue.put_nowait((value, target, mode, encoded_size))
                self._observer_bytes += encoded_size
            except Full:
                self._observer_dropped += 1
                return
            if self._thread is None:
                self._thread = Thread(target=self._observe, name="stratbox-observer", daemon=True)
                self._thread.start()

    def reserve_run(self, run_id: str) -> None:
        self.flush_transitions()
        self.source.reserve(run_id)

    def release_run(self, run_id: str) -> None:
        self.source.release(run_id)

    def acknowledge(self, through_offset: int) -> None:
        self.source.acknowledge(through_offset)

    def emit(self, kind, correlation: Correlation | None = None, **fields):
        # Also implements EventSink for the existing operation runner.
        if isinstance(kind, ExecutionEvent):
            record = record_from_execution_event(kind)
            if kind.kind == "operation.finished":
                with self._lock:
                    while len(self._finished_events) >= self._max_records:
                        self._finished_events.popitem(last=False)
                    self._finished_events[kind.invocation_id] = kind
            self._capture(record)
            return record
        if correlation is None:
            raise ValueError("orchestration.correlation_required")
        stamp = fields.pop("occurred_at_utc", None) or datetime.now(timezone.utc)
        counters = fields.get("counters")
        if isinstance(counters, dict):
            fields["counters"] = tuple(sorted(counters.items()))
        with self._lock:
            event = OrchestrationEvent(kind, self.session_id, self._sequence + 1,
                                       stamp, correlation, **fields)
            record = record_from_orchestration_event(event)
            validate_builtin_fields(record)
            if kind == "run.finished":
                # State transition and its immutable publication obligation are
                # retained together before invoking the journal source. Failure
                # changes observation health, never the computation outcome.
                if not self.source.has_reservation(record.correlation.run_id):
                    raise ValueError("journal.terminal_reservation_required")
                self._pending_transitions[record.record_id] = record
                self.flush_transitions()
            self._sequence = event.sequence
            self._capture(record)
            return record

    def capture_disposition(self, record):
        from stratbox.core.observability.capture.sinks import CaptureDisposition
        validate_builtin_fields(record)
        accepted = self._capture(record)
        return CaptureDisposition("accepted" if accepted else "dropped",
                                  "journal.accepted_in_memory" if accepted else "journal.capture_limit")

    def capture(self, record):
        return self.capture_disposition(record).accepted

    def capture_result(self, result, *, correlation=None):
        from stratbox.core.observability.capture.operations import capture_operation_result
        with self._lock:
            finished = self._finished_events.pop(result.invocation_id, None)
        for receipt in result.effects:
            try:
                self.confirmed_effect(correlation or (finished.correlation if finished is not None else Correlation()), receipt)
            except Exception:
                with self._lock:
                    self._publication_failures += 1
        return capture_operation_result(result, self, finished_event=finished, correlation=correlation)

    def capture_fact(self, fact, *, operation_id=None, invocation_id=None):
        from stratbox.core.observability.capture.adapters import record_from_fact
        return self.capture(record_from_fact(fact, operation_id=operation_id, invocation_id=invocation_id))

    def accepted_value(self, correlation, *, value_id, stage, role, identity,
                       source_id=None, qualification="reported", complete=True,
                       acceptance_id=None, occurred_at_utc=None):
        """Retain accepted state separately from lossy diagnostic observation."""
        from stratbox.core.observability.capture.adapters import record_from_fact
        from stratbox.core.observability.records.contracts import DomainFact, ObjectRef, make_fact_id
        payload = dict(data_version=1, value_id=value_id, stage=stage, role=role,
                       identity=dict(sha256=identity.sha256, size=identity.size),
                       source_id=source_id, qualification=qualification, complete=complete,
                       acceptance_id=acceptance_id or sha256(
                           f"{correlation.session_id}:{correlation.run_id}:{correlation.workflow_scope_id}:{correlation.task_id}:{value_id}".encode()).hexdigest())
        subject = ObjectRef("value", value_id, identity=identity)
        fact_id = make_fact_id("value.accepted", subject, payload)
        fact = DomainFact("value.accepted", subject, fact_id,
                          occurred_at_utc or datetime.now(timezone.utc), payload,
                          observation_id=fact_id, correlation=correlation)
        record = record_from_fact(fact)
        return self._publish_fact(record)

    def confirmed_effect(self, correlation, receipt):
        """Publish a confirmed destination receipt independently of computation."""
        if receipt.state != "confirmed" or receipt.effect_id is None:
            return None
        if receipt.kind.startswith(("notification.", "notifications.")):
            return None
        from stratbox.core.observability.capture.adapters import record_from_fact
        from stratbox.core.observability.records.contracts import DomainFact, ObjectRef, make_fact_id
        payload = dict(data_version=1, effect_id=receipt.effect_id,
            effect_kind=receipt.kind, state=receipt.state,
            identity=(dict(sha256=receipt.identity.sha256, size=receipt.identity.size) if receipt.identity is not None else None),
            destination_id=sha256(receipt.reference.encode()).hexdigest() if receipt.reference is not None else None,
            guarantee=receipt.guarantee, stage=receipt.stage)
        subject = ObjectRef("effect", receipt.effect_id, identity=receipt.identity)
        fact_id = make_fact_id("effect.confirmed", subject, payload)
        record = record_from_fact(DomainFact("effect.confirmed", subject, fact_id,
            datetime.now(timezone.utc), payload, observation_id=fact_id,
            correlation=replace(correlation, effect_id=receipt.effect_id)))
        return self._publish_fact(record)

    def _publish_fact(self, record):
        key = "fact." + record.fact_id
        with self._lock:
            existing = self.facts_source.lookup(key)
            if existing is not None:
                return existing.record
            if record.record_id in self._pending_transitions:
                pending = self._pending_transitions[record.record_id]
                self.flush_transitions()
                return pending
            # Capacity admission happens before publishing a promised fact.
            # The caller can retain accepted computation even if this separate
            # observation obligation cannot be admitted.
            if not self.facts_source.has_reservation(key):
                self.facts_source.reserve(key)
            self._pending_transitions[record.record_id] = record
            self.flush_transitions()
            self._capture(record)
        return record

    def flush_transitions(self) -> int:
        """Retry the same immutable transition identities without duplicate alerts."""
        with self._lock:
            published = 0
            for identity, record in tuple(self._pending_transitions.items()):
                try:
                    if record.kind in {"value.accepted", "effect.confirmed"}:
                        self.facts_source.append_fact(record)
                    else:
                        self.source.append_terminal(record)
                except Exception:
                    self._publication_failures += 1
                    continue
                del self._pending_transitions[identity]
                published += 1
            return published

    def _capture(self, record):
        encoded_size = len(encode_record(record))
        with self._lock:
            self._emitted += 1
            if encoded_size <= self._max_bytes:
                while self._records and (len(self._records) >= self._max_records
                        or self._bytes + encoded_size > self._max_bytes):
                    _, size = self._records.popleft()
                    self._bytes -= size
                    self._evicted += 1
                self._records.append((record, encoded_size))
                self._bytes += encoded_size
            else:
                self._evicted += 1
            if self._sink is not None:
                self._enqueue_observation(record, self._sink, "record", encoded_size)
            return encoded_size <= self._max_bytes

    def _observe(self):
        while not self._stop.is_set() or not self._queue.empty():
            try:
                value, target, mode, encoded_size = self._queue.get(timeout=0.05)
            except Empty:
                continue
            try:
                if mode == "event":
                    target.emit(value)
                elif hasattr(target, "capture"):
                    accepted = target.capture(value)
                    if accepted is False:
                        with self._lock:
                            self._observer_dropped += 1
                else:
                    target(value)
            except Exception:
                with self._lock:
                    self._observer_failed += 1
            finally:
                with self._lock:
                    self._observer_bytes -= encoded_size
                self._queue.task_done()

    @property
    def event_cursor(self):
        """Latest producer revision even when all prior ticks were evicted."""
        with self._lock:
            return self._sequence

    @property
    def records(self):
        with self._lock:
            return tuple(record for record, _ in self._records)

    def events(self, after: int = 0):
        """Scheduler records after the producer sequence; health reports gaps."""
        with self._lock:
            return tuple(record for record, _ in self._records
                         if record.record_type == "orchestration" and record.sequence > after)

    def health_snapshot(self) -> OrchestrationHealth:
        with self._lock:
            return OrchestrationHealth(self._emitted, len(self._records), self._evicted,
                                       self._observer_dropped, self._observer_failed,
                                       self.source.pending + self.facts_source.pending,
                                       self.source.reserved + self.facts_source.reserved,
                                       "incomplete" if self._evicted or self._observer_dropped or self._observer_failed
                                       or self._publication_failures or self._pending_transitions
                                       else "complete", len(self._pending_transitions), self._publication_failures)

    def close(self, *, timeout: float = 1.0) -> None:
        if timeout < 0:
            raise ValueError("orchestration.close_timeout_invalid")
        self.flush_transitions()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            if self._thread.is_alive():
                with self._lock:
                    self._observer_failed += 1
