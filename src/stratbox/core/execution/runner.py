from __future__ import annotations

from dataclasses import replace
from datetime import timezone
from collections import deque
from typing import Callable, Generic, Mapping, TypeVar
from uuid import uuid4

from stratbox.shared.data.datasets import ComputationReceipt, build_dataset_version, computation_identity
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.core.runtime.capabilities import BindingError, select_provider
from stratbox.core.limits import BudgetExceeded, BudgetMeter, ExecutionBudget
from stratbox.core.runtime.providers import RuntimeProviderError, active_providers
from stratbox.core.runtime.dependencies import MissingExtra

from stratbox.core.execution.contracts import (
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
from stratbox.core.execution.events import ExecutionEvent, TechnicalIncident
from stratbox.core.execution.effects import _EffectAccumulator
from stratbox.core.execution.resolution import _WorkCompletion, _resolve_completion

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
        self._effects = _EffectAccumulator()
        self._sealed = False
        self.parents: list[tuple[str, ComputationReceipt]] = []
        self.computation: ComputationReceipt | None = None

    @property
    def effects(self) -> tuple[EffectReceipt, ...]:
        """Read-only current receipt projection, in first-registration order."""
        return self._effects.snapshot()

    def _require_open(self) -> None:
        if self._sealed:
            raise RuntimeError("Invocation has already been finalized")

    def seal(self) -> None:
        self._sealed = True

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

    def provider(self, role: str, provider: object | None = None):
        if (
            provider is None and self.context.profile == "local"
            and role in {"http", "filestore", "output_filestore"}
            and not any(binding.capability.role == role for binding in self.context.bindings)
        ):
            defaults = active_providers()
            if defaults is not None:
                provider = defaults.http if role == "http" else defaults.filestore
        self.require_provider(role, provider)
        return provider

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
        self._require_open()
        self.check_cancelled()
        self._stage = safe_token(name)
        self._stage_started = self.context.clock.monotonic()
        self._progress_at = float("-inf")
        self._emit("operation.stage")

    def progress(self, completed: int, total: int | None = None) -> None:
        self._require_open()
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
        self._require_open()
        if receipt not in self.used_inputs:
            self.used_inputs.append(receipt)

    def record(self, identity, *, parameters=None, resources=None, inputs=None):
        self._require_open()
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
        self._require_open()
        if not isinstance(receipt, EffectReceipt) or receipt.kind not in self.definition.possible_effects:
            raise ValueError("Undeclared effect")
        self._effects.register(receipt)

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
        category = diagnostic.code.split(".", 1)[0]
        disposition = diagnostic.retry_disposition
        if disposition == "none" and category in {"budget", "http", "provider"}:
            disposition = "after_condition"
        # External effect uncertainty receives its own separate diagnostic.
        # A domain-level unknown (e.g. ambiguous workbook) is not a file retry.
        return replace(
            diagnostic,
            stage=diagnostic.stage or self._stage or "admission",
            component=diagnostic.component or category,
            reason_class=diagnostic.reason_class or category,
            retry_disposition=disposition,
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


def _execute_work(
    definition: OperationDefinition,
    request: R,
    work: Callable[[R, Invocation], T | Completion[T]],
    invocation: Invocation,
    providers: Mapping[str, object] | None,
) -> _WorkCompletion:
    try:
        invocation.check_cancelled()
        if not isinstance(request, definition.request_type):
            raise OperationFailure("request.invalid_type")
        available = providers if providers is not None else {}
        for role in sorted(definition.required_capabilities):
            invocation.provider(role, available.get(role))
        completed = work(request, invocation)
        if isinstance(completed, Completion):
            outcome, value, diagnostics = completed.outcome, completed.value, completed.diagnostics
        else:
            outcome, value, diagnostics = "succeeded", completed, ()

        # Retain the existing output-budget boundary: storage operations charge
        # their own output bytes at commit, so charging a second time here would
        # double-count them. Pure representations are charged once at completion.
        if outcome in {"succeeded", "partial"}:
            output = value if isinstance(value, Representation) else getattr(value, "representation", None)
            if isinstance(output, Representation):
                # Pure in-memory representations have not been charged by a
                # publishing provider. A publishing provider already charged
                # physical output at its own effect boundary.
                if not invocation.effects:
                    invocation.budget.charge(
                        "output_bytes", output.identity.size, completed=outcome == "partial"
                    )
                # Computation identity is distinct from external publication:
                # registering a confirmed effect must not suppress provenance.
                if invocation.computation is None:
                    invocation.record(
                        output.identity,
                        parameters={"profile": output.profile_id, "profile_version": output.version},
                    )
            elif outcome == "succeeded" and not definition.partial_allowed and not invocation.effects:
                invocation.budget.checkpoint()
        return _WorkCompletion(outcome, value, diagnostics)
    except OperationFailure as error:
        return _WorkCompletion(error.outcome, None, (error.diagnostic,))
    except (BudgetExceeded, BindingError, RuntimeProviderError) as error:
        return _WorkCompletion("failed", None, (Diagnostic(error.code),))
    except MissingExtra:
        return _WorkCompletion("failed", None, (Diagnostic("provider.capability_missing"),))
    except Exception as error:
        return _WorkCompletion("failed", None, (invocation.incident(error),))


def _validated_result(
    definition: OperationDefinition,
    invocation: Invocation,
    work_result: _WorkCompletion,
) -> OperationResult:
    effects = invocation.effects
    inputs = tuple(invocation.used_inputs)
    integrity = invocation._effects.integrity_diagnostics()
    resolved = _resolve_completion(
        definition, work_result, effects, integrity, invocation._effects.conflict_keys()
    )
    diagnostics = tuple(invocation.describe(item, resolved.outcome) for item in resolved.diagnostics)
    summary = ObservabilitySummary(
        invocation._emitted, invocation._dropped, invocation._incidents_dropped
    )
    try:
        # Validate *before* producing an irreversible terminal observation.
        return OperationResult(
            definition, invocation.id, resolved.outcome, resolved.value, diagnostics,
            inputs, effects, summary,
            invocation.computation if resolved.value is not None else None,
            invocation.budget.usage(),
        )
    except Exception as error:
        # A contract/finalizer defect must not emit a false successful finish.
        # Do not rerun the handler or any effect. Preserve qualified receipts.
        incident = invocation.incident(error)
        fallback = _resolve_completion(
            definition, _WorkCompletion("failed", None, (incident,)), effects, integrity,
            invocation._effects.conflict_keys(),
        )
        diagnostics = tuple(invocation.describe(item, fallback.outcome) for item in fallback.diagnostics)
        return OperationResult(
            definition, invocation.id, fallback.outcome, None, diagnostics,
            inputs, effects,
            ObservabilitySummary(invocation._emitted, invocation._dropped, invocation._incidents_dropped),
            None, invocation.budget.usage(),
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
    completed = _execute_work(definition, request, work, invocation, providers)
    invocation.seal()
    result = _validated_result(definition, invocation, completed)
    summary = invocation.finish(
        result.outcome, result.diagnostics[0] if result.diagnostics else None
    )
    # Only telemetry counters may change after validated finalization.
    return replace(result, observability=summary)
