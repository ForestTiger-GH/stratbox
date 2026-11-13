from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from threading import Lock
from typing import Literal, Protocol

from .contracts import Correlation, Outcome, safe_token


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    version: int
    kind: Literal[
        "operation.started",
        "operation.stage",
        "operation.progress",
        "operation.finished",
    ]
    invocation_id: str
    operation_id: str
    contract_version: int
    method_version: str
    sequence: int
    occurred_at_utc: datetime
    correlation: Correlation
    stage: str | None = None
    outcome: Outcome | None = None
    diagnostic_code: str | None = None
    duration_ms: int | None = None
    completed: int | None = None
    total: int | None = None
    reason_class: str | None = None
    stage_elapsed_ms: int | None = None
    incident_id: str | None = None

    def __post_init__(self) -> None:
        if self.version != 3 or self.kind not in {
            "operation.started",
            "operation.stage",
            "operation.progress",
            "operation.finished",
        }:
            raise ValueError("Unsupported event version or kind")
        if (
            self.occurred_at_utc.utcoffset() is None
            or self.occurred_at_utc.utcoffset().total_seconds() != 0
        ):
            raise ValueError("Execution events require UTC timestamps")
        for value in (self.sequence, self.contract_version):
            if type(value) is not int or not 0 < value <= 2**53 - 1:
                raise ValueError("Invalid event sequence or contract version")
        for value in (self.duration_ms, self.completed, self.total, self.stage_elapsed_ms):
            if value is not None and (
                type(value) is not int or not 0 <= value <= 2**53 - 1
            ):
                raise ValueError("Invalid event measurement")
        if (
            self.completed is not None
            and self.total is not None
            and self.completed > self.total
        ):
            raise ValueError("Invalid event progress")
        if not isinstance(self.correlation, Correlation):
            raise ValueError("Invalid event correlation")
        if self.outcome is not None and self.outcome not in {
            "succeeded",
            "partial",
            "failed",
            "cancelled",
            "unknown",
        }:
            raise ValueError("Invalid event outcome")
        for token in (
            self.invocation_id,
            self.operation_id,
            self.method_version,
            self.stage,
            self.diagnostic_code,
            self.reason_class,
            self.incident_id,
            self.outcome,
        ):
            if token is not None:
                safe_token(token)

    @property
    def event_id(self) -> str:
        return f"{self.invocation_id}.{self.sequence}"

    def to_json(self) -> str:
        # Project only the base record's fields, even for subclasses.
        value = {
            name: getattr(self, name) for name in ExecutionEvent.__dataclass_fields__
        }
        value["occurred_at_utc"] = self.occurred_at_utc.isoformat()
        value["correlation"] = {
            name: getattr(self.correlation, name)
            for name in Correlation.__dataclass_fields__
        }
        return json.dumps(
            value, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        )


class EventSink(Protocol):
    def emit(self, event: ExecutionEvent) -> None: ...


@dataclass(frozen=True, slots=True)
class TechnicalIncident:
    incident_id: str
    invocation_id: str
    operation_id: str
    stage: str
    exception_type: str
    frames: tuple[tuple[str, int], ...]


class IncidentSink(Protocol):
    def emit(self, incident: TechnicalIncident) -> None: ...


class InMemorySink:
    def __init__(self) -> None:
        self._events: list[ExecutionEvent] = []
        self._lock = Lock()

    def emit(self, event: ExecutionEvent) -> None:
        with self._lock:
            self._events.append(event)

    @property
    def events(self) -> tuple[ExecutionEvent, ...]:
        with self._lock:
            return tuple(self._events)
