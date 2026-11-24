"""Typed scheduler observations with no fabricated operation invocation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from stratbox.core.execution.contracts import Correlation
from stratbox.core.observability.records.contracts import JournalRecord, ObjectRef, require_utc
from stratbox.shared.identifiers import safe_token

ORCHESTRATION_KINDS = frozenset({
    "run.queued", "run.admitted", "run.started", "run.cancelling", "run.finished",
    "scope.started", "scope.finished", "scope.blocked",
    "task.waiting", "task.ready", "task.started", "task.retry", "task.finished",
    "task.blocked", "task.skipped", "collection.expanded", "collection.closed",
    "map.expanded", "map.closed", "shared_work.started", "shared_work.finished",
    "shared_work.attached", "shared_work.detached", "shared_work.reused",
})
OUTCOMES = frozenset({"succeeded", "partial", "failed", "cancelled", "unknown"})
COUNTERS = ("discovered", "admitted", "waiting", "running", "succeeded", "partial",
            "failed", "cancelled", "unknown", "blocked", "skipped", "retries", "reused",
            "physical_work", "logical_uses", "physical_transfers", "running_physical")


@dataclass(frozen=True, slots=True)
class OrchestrationEvent:
    kind: str
    producer_id: str
    sequence: int
    occurred_at_utc: datetime
    correlation: Correlation
    state: str | None = None
    reason: str | None = None
    outcome: str | None = None
    completed: int | None = None
    total: int | None = None
    counters: tuple[tuple[str, int], ...] = ()
    invocation_id: str | None = None
    operation_id: str | None = None
    references: tuple[ObjectRef, ...] = ()
    service: bool = False
    denominator_open: bool = False

    def __post_init__(self) -> None:
        if type(self.denominator_open) is not bool:
            raise ValueError("orchestration.denominator_invalid")
        if self.denominator_open and self.total is not None:
            raise ValueError("orchestration.open_denominator_has_total")
        if type(self.service) is not bool:
            raise ValueError("orchestration.service_invalid")
        if self.kind not in ORCHESTRATION_KINDS:
            raise ValueError("orchestration.kind_invalid")
        if type(self.sequence) is not int or not 1 <= self.sequence < 2**53:
            raise ValueError("orchestration.sequence_invalid")
        require_utc(self.occurred_at_utc)
        if not isinstance(self.correlation, Correlation) or self.correlation.session_id is None:
            raise ValueError("orchestration.session_required")
        if self.kind.startswith(("run.", "task.", "scope.", "collection.", "map.")) and self.correlation.run_id is None:
            raise ValueError("orchestration.run_required")
        if self.kind.startswith("task.") and self.correlation.task_id is None:
            raise ValueError("orchestration.task_required")
        if self.kind.startswith("shared_work.") and self.correlation.shared_work_id is None:
            raise ValueError("orchestration.shared_work_required")
        for token in (self.producer_id, self.state, self.reason, self.invocation_id, self.operation_id):
            if token is not None:
                safe_token(token)
        if self.outcome is not None and self.outcome not in OUTCOMES:
            raise ValueError("orchestration.outcome_invalid")
        if self.kind == "run.finished" and self.outcome is None:
            raise ValueError("orchestration.terminal_outcome_required")
        for count in (self.completed, self.total):
            if count is not None and (type(count) is not int or not 0 <= count < 2**53):
                raise ValueError("orchestration.count_invalid")
        if self.completed is not None and self.total is not None and self.completed > self.total:
            raise ValueError("orchestration.progress_invalid")
        if (not isinstance(self.counters, tuple) or len(self.counters) > len(COUNTERS)
                or len({key for key, _ in self.counters}) != len(self.counters)):
            raise ValueError("orchestration.counters_invalid")
        for key, count in self.counters:
            if key not in COUNTERS or type(count) is not int or not 0 <= count < 2**53:
                raise ValueError("orchestration.counters_invalid")
        if not isinstance(self.references, tuple) or len(self.references) > 64 or any(
                not isinstance(ref, ObjectRef) for ref in self.references):
            raise ValueError("orchestration.references_invalid")

    @property
    def event_id(self) -> str:
        return sha256(f"{self.producer_id}:{self.sequence}".encode()).hexdigest()


def record_from_orchestration_event(event: OrchestrationEvent) -> JournalRecord:
    payload = {
        "data_version": 1, "producer_id": event.producer_id,
        "state": event.state, "reason": event.reason, "outcome": event.outcome,
        "completed": event.completed, "total": event.total,
        "counters": dict(event.counters), "invocation_id": event.invocation_id,
        "operation_id": event.operation_id, "service": event.service,
        "denominator_open": event.denominator_open,
    }
    if event.kind == "run.finished":
        payload.update(run_id=event.correlation.run_id, plan_id=event.correlation.plan_id,
                       transition_id=event.event_id)
    causes = (event.correlation.cause_event_id,) if event.correlation.cause_event_id else ()
    return JournalRecord(event.event_id, "orchestration", event.kind,
                         event.occurred_at_utc, payload, correlation=event.correlation,
                         references=event.references, cause_record_ids=causes,
                         outcome=event.outcome, sequence=event.sequence)
