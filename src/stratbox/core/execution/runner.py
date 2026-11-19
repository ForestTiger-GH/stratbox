from __future__ import annotations

from dataclasses import replace
from datetime import timezone
from math import isfinite
from collections import deque
from typing import Callable, Generic, Mapping, Sequence, TypeVar
from uuid import uuid4

from stratbox.shared.data.datasets import ComputationReceipt, build_dataset_version, computation_identity
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.core.runtime.capabilities import BindingError, select_provider
from stratbox.core.limits import BudgetError, BudgetClockError, BudgetExceeded, BudgetMeter, ExecutionBudget
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
from stratbox.core.execution.resolution import _WorkCompletion, _resolve_completion, _terminal_constraint

T = TypeVar("T")
R = TypeVar("R")


class Invocation:
    def __init__(self, definition: OperationDefinition, context: ExecutionContext):
        self.definition = definition
        self.context = context
        self.id = uuid4().hex
        self._started = context.clock.monotonic()
        if type(self._started) not in (int, float) or not isfinite(self._started):
            raise ValueError("Invalid execution clock at admission")
        self.budget = BudgetMeter(
            ExecutionBudget.intersect(definition.limits, context.ceiling, context.budget),
            now=context.clock.monotonic,
        )
        self._progress_at = float("-inf")
        self._sequence = self._emitted = self._dropped = 0
        self._incidents_dropped = 0
        self._timing_degraded = False
        self._stage: str | None = None
        self._stage_started: float | None = self._started
        self.used_inputs: list[UsedInputReceipt] = []
        self._input_index: set[UsedInputReceipt] = set()
        self._effects = _EffectAccumulator()
        self._effect_view = self._effects.view()
        self._sealed = False
        self._terminal_emitted = False
        self.parents: list[tuple[str, ComputationReceipt]] = []
        self.computation: ComputationReceipt | None = None

    @property
    def effects(self) -> Sequence[EffectReceipt]:
        """Live read-only receipt view, in first-registration order."""
        return self._effect_view

    def _require_open(self) -> None:
        if self._sealed:
            raise RuntimeError("Invocation has already been finalized")

    def _seal(self) -> None:
        if self._sealed:
            raise RuntimeError("Invocation has already been finalized")
        self._sealed = True
        self.used_inputs = tuple(self.used_inputs)

    def _telemetry_tick(self) -> float | None:
        """Best-effort sample. It must never decide the operation outcome."""
        if self.context.sink is None:
            return None
        try:
            value = self.context.clock.monotonic()
            if type(value) not in (int, float) or not isfinite(value):
                raise ValueError("Invalid telemetry timestamp")
            return value
        except Exception:
            self._timing_degraded = True
            return None

    def _elapsed_ms(self, started: float | None) -> int | None:
        if started is None:
            return None
        try:
            elapsed = self.context.clock.monotonic() - started
            if not isfinite(elapsed) or not 0 <= elapsed <= (2**53 - 1) / 1000:
                raise ValueError("Invalid monotonic measurement")
            return int(elapsed * 1000)
        except Exception:
            self._timing_degraded = True
            return None

    def _summary(self) -> ObservabilitySummary:
        return ObservabilitySummary(
            self._emitted, self._dropped, self._incidents_dropped, self._timing_degraded,
        )

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
        self._declared_provider(role)
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

    def _declared_provider(self, role: str) -> None:
        if role not in self.definition.required_capabilities | self.definition.optional_capabilities:
            raise OperationFailure("provider.capability_undeclared")

    def require_provider(self, role: str, provider: object) -> None:
        self._declared_provider(role)
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
        name = safe_token(name)
        self.check_cancelled()
        self._stage = name
        self._stage_started = self._telemetry_tick()
        self._progress_at = float("-inf")
        self._emit("operation.stage")

    def progress(self, completed: int, total: int | None = None) -> None:
        self._require_open()
        # Validate caller input before touching cancellation/deadline clocks.
        if type(completed) is not int or not 0 <= completed <= 2**53 - 1 or (
            total is not None and (
                type(total) is not int or not completed <= total <= 2**53 - 1
            )
        ):
            raise ValueError("Invalid progress counters")
        self.check_cancelled()
        if self.context.sink is None:
            return
        sampled = self._telemetry_tick()
        if sampled is None:
            # Without a valid throttle time, omit optional progress events.
            return
        if sampled - self._progress_at >= 0.25 or completed == total:
            self._progress_at = sampled
            self._emit("operation.progress", completed=completed, total=total)

    def use(self, receipt: UsedInputReceipt) -> None:
        self._require_open()
        if not isinstance(receipt, UsedInputReceipt):
            raise TypeError("Expected a qualified input receipt")
        if receipt not in self._input_index:
            self._input_index.add(receipt)
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

    def account_output(
        self, identity, *, key: str = "returned", covered_by: str | None = None,
        completed: bool = False,
    ) -> None:
        """Charge a specific output once; an explicit alias proves coverage."""
        self._require_open()
        self.budget.account_output(key, identity, covered_by=covered_by, completed=completed)

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
            timestamp = self.now()
        except Exception:
            # No fabricated UTC timestamps when the supplied clock fails.
            self._timing_degraded = True
            self._dropped += 1
            return
        stage_elapsed = self._elapsed_ms(self._stage_started) if self._stage else None
        try:
            event = ExecutionEvent(
                3, kind, self.id, self.definition.operation_id,
                self.definition.contract_version, self.definition.method_version,
                self._sequence, timestamp, self.context.correlation,
                stage=self._stage, stage_elapsed_ms=stage_elapsed, **fields,
            )
            sink.emit(event)
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

    def _finish(self, outcome: Outcome, diagnostic: Diagnostic | None) -> ObservabilitySummary:
        if not self._sealed or self._terminal_emitted:
            raise RuntimeError("Invalid terminal observation transition")
        self._terminal_emitted = True
        elapsed = self._elapsed_ms(self._started) if self.context.sink is not None else None
        self._emit(
            "operation.finished",
            outcome=outcome,
            diagnostic_code=diagnostic.code if diagnostic else None,
            reason_class=diagnostic.reason_class if diagnostic else None,
            incident_id=diagnostic.incident_id if diagnostic else None,
            duration_ms=elapsed,
        )
        return self._summary()


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
                invocation.account_output(
                    output.identity, key="returned", completed=True,
                )
                # Computation identity is distinct from external publication:
                # registering a confirmed effect must not suppress provenance.
                if invocation.computation is None:
                    invocation.record(
                        output.identity,
                        parameters={"profile": output.profile_id, "profile_version": output.version},
                    )
        return _WorkCompletion(outcome, value, diagnostics)
    except OperationFailure as error:
        return _WorkCompletion(error.outcome, None, (error.diagnostic,))
    except (BudgetError, BindingError, RuntimeProviderError) as error:
        return _WorkCompletion("failed", None, (Diagnostic(error.code),))
    except MissingExtra:
        return _WorkCompletion("failed", None, (Diagnostic("provider.capability_missing"),))
    except Exception as error:
        return _WorkCompletion("failed", None, (invocation.incident(error),))


def _terminal_budget(invocation: Invocation, work_result: _WorkCompletion) -> _WorkCompletion:
    """Check the deadline alone, without re-reading a late cancellation token."""
    if invocation.budget.limits.seconds is None:
        return work_result
    try:
        invocation.budget.checkpoint()
    except BudgetError as exc:
        if isinstance(exc, BudgetClockError):
            invocation._timing_degraded = True
        return _terminal_constraint(work_result, Diagnostic(exc.code))
    except Exception:
        invocation._timing_degraded = True
        return _terminal_constraint(work_result, Diagnostic("budget.clock_unavailable"))
    return work_result


def _validated_result(
    definition: OperationDefinition,
    invocation: Invocation,
    work_result: _WorkCompletion,
) -> OperationResult:
    effects = invocation._effects.snapshot()
    inputs = tuple(invocation.used_inputs)
    integrity = invocation._effects.integrity_diagnostics()
    conflict_keys = invocation._effects.conflict_keys()
    try:
        resolved = _resolve_completion(
            definition, work_result, effects, integrity, conflict_keys,
        )
        diagnostics = tuple(invocation.describe(item, resolved.outcome)
                            for item in resolved.diagnostics)
        return OperationResult(
            definition, invocation.id, resolved.outcome, resolved.value, diagnostics,
            inputs, effects, invocation._summary(), invocation.computation,
            invocation.budget.usage(),
        )
    except Exception as error:
        incident = invocation.incident(error)
        unresolved = bool(conflict_keys) or any(e.state == "unknown" for e in effects)
        outcome: Outcome = "unknown" if unresolved else "failed"
        diagnostics = list(work_result.diagnostics)
        diagnostics.extend(integrity)
        for effect in effects:
            if effect.state == "unknown" and (effect.kind, effect.effect_id) not in conflict_keys:
                diagnostics.append(Diagnostic(
                    "effect.outcome_unknown", component=effect.kind, evidence_ref=effect.effect_id,
                    reconciliation_owner=effect.reconciliation_owner,
                    retry_disposition="reconcile" if effect.effect_id else "none",
                ))
        diagnostics.append(incident)
        fallback = tuple(diagnostics)
        try:
            return OperationResult(
                definition, invocation.id, outcome, None, fallback, inputs,
                effects, invocation._summary(), invocation.computation,
                invocation.budget.usage(),
            )
        except Exception:
            # A patched/failed constructor cannot erase a known effect.
            from stratbox.core.execution.contracts import OperationResult as ValidatedResult
            return ValidatedResult(
                definition, invocation.id, outcome, None, fallback, inputs,
                effects, invocation._summary(), invocation.computation,
                invocation.budget.usage(),
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
    completed = _terminal_budget(invocation, completed)
    try:
        invocation._seal()
    except Exception as error:
        completed = _WorkCompletion(
            "failed", None, completed.diagnostics + (invocation.incident(error),),
        )
        invocation._sealed = True
        invocation.used_inputs = tuple(invocation.used_inputs)
    result = _validated_result(definition, invocation, completed)
    try:
        summary = invocation._finish(
            result.outcome, result.diagnostics[0] if result.diagnostics else None
        )
    except Exception:
        # A terminal event might have been accepted; never retry the emission.
        invocation._timing_degraded = True
        invocation._dropped += 1
        summary = invocation._summary()
    return replace(result, observability=summary)
