"""Optional in-memory capture and isolated composite execution-event observation."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
from typing import Callable

from stratbox.execution import ExecutionEvent, EventSink, OperationResult
from .adapters import record_from_execution_event, record_from_fact, record_from_result
from .contracts import DomainFact, JournalRecord
from .policies import CapturePolicy


class RecordMemorySink:
    def __init__(self, policy: CapturePolicy | None = None):
        self.policy = policy or CapturePolicy()
        self._records: list[JournalRecord] = []
        self._bytes_used = 0
        self._dropped = 0
        self._lock = RLock()

    def capture(self, record: JournalRecord) -> bool:
        if not self.policy.accepts(record):
            return False
        from .codecs import encode_record
        try:
            byte_size = len(encode_record(record))
        except ValueError:
            with self._lock:
                self._dropped += 1
            return False
        with self._lock:
            if len(self._records) >= self.policy.max_records or self._bytes_used + byte_size > self.policy.max_bytes:
                self._dropped += 1
                return False
            self._records.append(record)
            self._bytes_used += byte_size
            return True

    def emit(self, event: ExecutionEvent) -> None:
        self.capture(record_from_execution_event(event))

    def capture_fact(self, fact: DomainFact, *, operation_id: str | None = None,
                     invocation_id: str | None = None) -> bool:
        return self.capture(record_from_fact(fact, operation_id=operation_id, invocation_id=invocation_id))

    def capture_result(self, result: OperationResult, **kwargs) -> bool:
        return self.capture(record_from_result(result, **kwargs))

    @property
    def records(self) -> tuple[JournalRecord, ...]:
        with self._lock:
            return tuple(self._records)

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._dropped

    @property
    def bytes_used(self) -> int:
        with self._lock:
            return self._bytes_used


class CompositeEventSink:
    """Best-effort fanout; sink failures cannot stop sibling recipients."""
    def __init__(self, *sinks: EventSink):
        self.sinks = tuple(sinks)
        self._lock = RLock()
        self._dropped = 0

    def emit(self, event: ExecutionEvent) -> None:
        for sink in self.sinks:
            try:
                sink.emit(event)
            except Exception:
                with self._lock:
                    self._dropped += 1

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._dropped


class FileEventSink:
    """Best-effort execution sink backed by an explicit buffered file journal.

    The operation runner catches emit errors as before. A caller requiring
    durability must inspect explicit flush/close receipts, never infer it from
    a successful operation result.
    """
    def __init__(self, journal, policy: CapturePolicy | None = None):
        self.journal = journal
        self.policy = policy or CapturePolicy()
        self._lock = RLock()
        self._dropped = 0

    def capture(self, record: JournalRecord) -> bool:
        if not self.policy.accepts(record):
            return False
        with self._lock:
            try:
                receipt = self.journal.append(record)
                if receipt is not None and receipt.state != "confirmed":
                    raise RuntimeError("Journal segment publication unconfirmed")
            except Exception:
                self._dropped += 1
                raise
            return True

    def emit(self, event: ExecutionEvent) -> None:
        self.capture(record_from_execution_event(event))

    def flush(self):
        with self._lock:
            return self.journal.flush()

    def close(self):
        with self._lock:
            return self.journal.close()

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._dropped
