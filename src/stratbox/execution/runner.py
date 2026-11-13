from __future__ import annotations

from dataclasses import replace
from datetime import timezone
from collections import deque
from typing import Callable, Generic, Mapping, TypeVar
from uuid import uuid4

from stratbox.data import ComputationReceipt, Representation, UsedInputReceipt, build_dataset_version, computation_identity
from stratbox.base.capabilities import BindingError, select_provider
from stratbox.base.limits import BudgetExceeded, BudgetMeter, ExecutionBudget
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
from .events import ExecutionEvent, TechnicalIncident

T = TypeVar("T")
R = TypeVar("R")


class Invocation:
    def __init__(self, definition: OperationDefinition, context: ExecutionContext):
        self.definition = definition
        self.context = context
        self.id = uuid4().hex
        self._started = context.clock.monotonic()
        self.budget = BudgetMeter(
            ExecutionBudget.intersect(definition.limits, context.ceiling, context.budget),
            now=context.clock.monotonic,
        )
        self._progress_at = float("-inf")
        self._sequence = self._emitted = self._dropped = 0
        self._incidents_dropped = 0
        self._stage: str | None = None
        self._stage_started = self._started
        self.used_inputs: list[UsedInputReceipt] = []
        self.effects: list[EffectReceipt] = []
        self.parents: list[tuple[str, ComputationReceipt]] = []
        self.computation: ComputationReceipt | None = None

    def now(self):
        value = self.context.clock.now()
        if value.utcoffset() is None:
            raise ValueError("Execution clock requires timezone-aware time")
        return value.astimezone(timezone.utc)

    def check_cancelled(self) -> None:
        if self.cancelled():
            raise OperationFailure("operation.cancelled", outcome="cancelled")
        self.budget.checkpoint()

    def cancelled(self) -> bool:
        token = self.context.cancellation
        return token is not None and token.is_set()

    def incident(self, error: Exception) -> Diagnostic:
        incident_id = uuid4().hex
        sink = self.context.incident_sink
        if sink is not None:
            try:
                frames = deque(maxlen=12)
                trace = error.__traceback__
                while trace is not None:
                    frames.append((trace.tb_frame.f_code.co_name[:128], trace.tb_lineno))
                    trace = trace.tb_next
                sink.emit(TechnicalIncident(
                    incident_id, self.id, self.definition.operation_id, self._stage or "admission",
                    type(error).__name__[:128], tuple(frames),
                ))
            except Exception:
                self._incidents_dropped += 1
        return Diagnostic("internal.error", incident_id=incident_id)

    def require_provider(self, role: str, provider: object) -> None:
        if provider is None:
            raise OperationFailure("provider.capability_missing")
        managed = self.context.profile == "managed"
        bindings = self.context.bindings
        if not managed and not any(binding.capability.role == role for binding in bindings):
            return
        binding = select_provider(self.definition.capability(role, managed=managed), bindings)
        if binding.provider is not provider:
            raise OperationFailure("provider.binding_mismatch")

    def stage(self, name: str) -> None:
        self.check_cancelled()
        self._stage = safe_token(name)
        self._stage_started = self.context.clock.monotonic()
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

    def record(self, identity, *, parameters=None, resources=None, inputs=None):
        definition = self.definition
        receipts = tuple(self.used_inputs) if inputs is None else inputs
        version = build_dataset_version(
            definition.operation_id,
            f"contract-{definition.contract_version}",
            definition.method_version,
            receipts,
            identity,
            parameters=parameters,
            resources=resources,
        )
        computation_id = computation_identity(
            definition.operation_id, definition.contract_version, definition.method_version,
            receipts, parameters=parameters, resources=resources,
        )
        self.computation = ComputationReceipt(version, identity, receipts, computation_id, tuple(self.parents))
        return self.computation

    def effect(self, receipt: EffectReceipt) -> None:
        if receipt.kind not in self.definition.possible_effects:
            raise ValueError("Undeclared effect")
        for index, existing in enumerate(self.effects):
            if existing.effect_id == receipt.effect_id and existing.kind == receipt.kind:
                self.effects[index] = receipt
                return
        self.effects.append(receipt)

    def _emit(self, kind, **fields) -> None:
        sink = self.context.sink
        if sink is None:
            return
        self._sequence += 1
        try:
            sink.emit(
                ExecutionEvent(
                    3,
                    kind,
                    self.id,
                    self.definition.operation_id,
                    self.definition.contract_version,
                    self.definition.method_version,
                    self._sequence,
                    self.now(),
                    self.context.correlation,
                    stage=self._stage,
                    stage_elapsed_ms=(
                        max(0, int((self.context.clock.monotonic() - self._stage_started) * 1000))
                        if self._stage is not None else None
                    ),
                    **fields,
                )
            )
        except Exception:
            self._dropped += 1
        else:
            self._emitted += 1

    def describe(self, diagnostic: Diagnostic, outcome: Outcome) -> Diagnostic:
        effect = next((item for item in reversed(self.effects) if item.state == "unknown"), None)
        category = diagnostic.code.split(".", 1)[0]
        return replace(
            diagnostic,
            stage=diagnostic.stage or self._stage or "admission",
            component=diagnostic.component or category,
            reason_class=diagnostic.reason_class or category,
            retry_disposition="reconcile" if outcome == "unknown" or effect else
                "after_condition" if category in {"budget", "http", "provider"} else "none",
            evidence_ref=diagnostic.evidence_ref or (effect.effect_id if effect else None),
            reconciliation_owner=diagnostic.reconciliation_owner or (
                effect.reconciliation_owner if effect else None
            ),
        )

    def finish(self, outcome: Outcome, diagnostic: Diagnostic | None) -> ObservabilitySummary:
        elapsed = max(0, int((self.context.clock.monotonic() - self._started) * 1000))
        self._emit(
            "operation.finished",
            outcome=outcome,
            diagnostic_code=diagnostic.code if diagnostic else None,
            reason_class=diagnostic.reason_class if diagnostic else None,
            incident_id=diagnostic.incident_id if diagnostic else None,
            duration_ms=elapsed,
        )
        return ObservabilitySummary(self._emitted, self._dropped, self._incidents_dropped)


class Completion(Generic[T]):
    """A value with a qualified incomplete outcome."""

    def __init__(self, value: T, outcome: Outcome, *diagnostics: str | Diagnostic):
        if outcome not in {"partial", "unknown", "failed"} or not diagnostics:
            raise ValueError(
                "Incomplete completion requires an outcome and diagnostics"
            )
        self.value = value
        self.outcome = outcome
        self.diagnostics = tuple(
            item if isinstance(item, Diagnostic) else Diagnostic(item) for item in diagnostics
        )


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
        for role in sorted(definition.required_capabilities):
            invocation.require_provider(role, available.get(role))
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
        if outcome in {"succeeded", "partial"} and not invocation.effects:
            output = value if isinstance(value, Representation) else getattr(value, "representation", None)
            if isinstance(output, Representation):
                invocation.budget.charge("output_bytes", output.identity.size, completed=outcome == "partial")
                if invocation.computation is None:
                    invocation.record(output.identity, parameters={"profile": output.profile_id,
                                                                    "profile_version": output.version})
            elif outcome == "succeeded" and not definition.partial_allowed:
                invocation.budget.checkpoint()
    except OperationFailure as error:
        outcome, diagnostics, value = error.outcome, (error.diagnostic,), None
    except (BudgetExceeded, BindingError) as error:
        outcome, diagnostics, value = "failed", (Diagnostic(error.code),), None
    except MissingExtra:
        outcome, diagnostics, value = (
            "failed",
            (Diagnostic("provider.capability_missing"),),
            None,
        )
    except Exception as error:
        outcome, diagnostics, value = "failed", (invocation.incident(error),), None
    if any(effect.state == "unknown" for effect in invocation.effects):
        outcome = "unknown"
        diagnostics = diagnostics or (Diagnostic("effect.outcome_unknown"),)
    diagnostics = tuple(invocation.describe(item, outcome) for item in diagnostics)
    summary = invocation.finish(outcome, diagnostics[0] if diagnostics else None)
    return OperationResult(
        definition,
        invocation.id,
        outcome,
        value,
        diagnostics,
        tuple(invocation.used_inputs),
        tuple(invocation.effects),
        summary,
        invocation.computation if value is not None else None,
        invocation.budget.usage(),
    )
