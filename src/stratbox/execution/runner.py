from __future__ import annotations

from datetime import timezone
from typing import Callable, Generic, Mapping, TypeVar
from uuid import uuid4

from stratbox.data import UsedInputReceipt
from stratbox.base.utils.optional_deps import MissingExtra

from .contracts import (
    Diagnostic,
    EffectReceipt,
    ExecutionContext,
    ObservabilitySummary,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    Outcome,
    safe_token,
)
from .events import ExecutionEvent

T = TypeVar("T")
R = TypeVar("R")


class Invocation:
    def __init__(self, definition: OperationDefinition, context: ExecutionContext):
        self.definition = definition
        self.context = context
        self.id = uuid4().hex
        self._started = context.clock.monotonic()
        self._progress_at = float("-inf")
        self._sequence = self._emitted = self._dropped = 0
        self._stage: str | None = None
        self.used_inputs: list[UsedInputReceipt] = []
        self.effects: list[EffectReceipt] = []

    def now(self):
        value = self.context.clock.now()
        if value.utcoffset() is None:
            raise ValueError("Execution clock requires timezone-aware time")
        return value.astimezone(timezone.utc)

    def check_cancelled(self) -> None:
        if self.context.cancellation is not None and self.context.cancellation.is_set():
            raise OperationFailure("operation.cancelled", outcome="cancelled")

    def stage(self, name: str) -> None:
        self.check_cancelled()
        self._stage = safe_token(name)
        self._progress_at = float("-inf")
        self._emit("operation.stage")

    def progress(self, completed: int, total: int | None = None) -> None:
        self.check_cancelled()
        if not 0 <= completed <= 2**53 - 1 or (
            total is not None and not completed <= total <= 2**53 - 1
        ):
            raise ValueError("Invalid progress counters")
        now = self.context.clock.monotonic()
        if now - self._progress_at >= 0.25 or completed == total:
            self._progress_at = now
            self._emit("operation.progress", completed=completed, total=total)

    def use(self, receipt: UsedInputReceipt) -> None:
        if receipt not in self.used_inputs:
            self.used_inputs.append(receipt)

    def _emit(self, kind, **fields) -> None:
        sink = self.context.sink
        if sink is None:
            return
        self._sequence += 1
        try:
            sink.emit(
                ExecutionEvent(
                    1,
                    kind,
                    self.id,
                    self.definition.operation_id,
                    self.definition.contract_version,
                    self.definition.method_version,
                    self._sequence,
                    self.now(),
                    self.context.correlation,
                    stage=self._stage,
                    **fields,
                )
            )
        except Exception:
            self._dropped += 1
        else:
            self._emitted += 1

    def finish(self, outcome: Outcome, code: str | None) -> ObservabilitySummary:
        elapsed = max(0, int((self.context.clock.monotonic() - self._started) * 1000))
        self._emit(
            "operation.finished",
            outcome=outcome,
            diagnostic_code=code,
            duration_ms=elapsed,
        )
        return ObservabilitySummary(self._emitted, self._dropped)


class Completion(Generic[T]):
    """A value with a qualified incomplete outcome."""

    def __init__(self, value: T, outcome: Outcome, *diagnostics: str):
        if outcome not in {"partial", "unknown", "failed"} or not diagnostics:
            raise ValueError(
                "Incomplete completion requires an outcome and diagnostics"
            )
        self.value = value
        self.outcome = outcome
        self.diagnostics = tuple(Diagnostic(code) for code in diagnostics)


def run(
    definition: OperationDefinition,
    request: R,
    work: Callable[[R, Invocation], T | Completion[T]],
    *,
    context: ExecutionContext | None = None,
    providers: Mapping[str, object] | None = None,
) -> OperationResult[T]:
    invocation = Invocation(
        definition, context if context is not None else ExecutionContext()
    )
    invocation._emit("operation.started")
    outcome: Outcome = "succeeded"
    diagnostics: tuple[Diagnostic, ...] = ()
    value = None
    try:
        invocation.check_cancelled()
        if not isinstance(request, definition.request_type):
            raise OperationFailure("request.invalid_type")
        available = providers if providers is not None else {}
        if any(available.get(key) is None for key in definition.required_capabilities):
            raise OperationFailure("provider.capability_missing")
        completed = work(request, invocation)
        if isinstance(completed, Completion):
            outcome, value, diagnostics = (
                completed.outcome,
                completed.value,
                completed.diagnostics,
            )
        else:
            value = completed
        if not isinstance(value, definition.value_type) or (
            outcome == "partial" and not definition.partial_allowed
        ):
            raise TypeError("Operation returned a value outside its contract")
    except OperationFailure as error:
        outcome, diagnostics, value = error.outcome, (error.diagnostic,), None
    except MissingExtra:
        outcome, diagnostics, value = (
            "failed",
            (Diagnostic("provider.capability_missing"),),
            None,
        )
    except Exception:
        outcome, diagnostics, value = "failed", (Diagnostic("internal.error"),), None
    if outcome == "cancelled" and any(
        effect.state == "unknown" for effect in invocation.effects
    ):
        outcome, diagnostics = "unknown", (Diagnostic("effect.outcome_unknown"),)
    summary = invocation.finish(outcome, diagnostics[0].code if diagnostics else None)
    return OperationResult(
        definition,
        invocation.id,
        outcome,
        value,
        diagnostics,
        tuple(invocation.used_inputs),
        tuple(invocation.effects),
        summary,
    )
