"""Pure final-outcome resolution for a single operation invocation.

Only a domain handler may declare a useful partial result. External uncertainty
or contradictory receipts must never be promoted to a successful outcome.
"""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.core.execution.contracts import Diagnostic, EffectReceipt, OperationDefinition, Outcome


@dataclass(frozen=True, slots=True)
class _WorkCompletion:
    outcome: Outcome
    value: object | None
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class _ResolvedCompletion:
    outcome: Outcome
    value: object | None
    diagnostics: tuple[Diagnostic, ...]


def _terminal_constraint(
    work: _WorkCompletion, diagnostic: Diagnostic,
) -> _WorkCompletion:
    """Late budget violations never undo already-confirmed effects."""
    outcome = "failed" if work.outcome == "succeeded" else work.outcome
    return _WorkCompletion(outcome, work.value, work.diagnostics + (diagnostic,))


def _resolve_completion(
    definition: OperationDefinition,
    work: _WorkCompletion,
    effects: tuple[EffectReceipt, ...],
    integrity_diagnostics: tuple[Diagnostic, ...] = (),
    conflict_keys: frozenset[tuple[str, str]] = frozenset(),
) -> _ResolvedCompletion:
    outcome, value = work.outcome, work.value
    diagnostics = list(work.diagnostics)
    # Treat an invalid *handler* result as a contract failure before applying
    # effect precedence. Unknown external effects still take priority.
    invalid_value = value is not None and not isinstance(value, definition.value_type)
    missing_value = outcome in {"succeeded", "partial"} and value is None
    illegal_partial = outcome == "partial" and not definition.partial_allowed
    illegal_cancelled_value = outcome == "cancelled" and value is not None
    if invalid_value or missing_value or illegal_partial or illegal_cancelled_value:
        outcome, value = "failed", None
        diagnostics.append(Diagnostic("internal.error"))

    for diagnostic in integrity_diagnostics:
        if diagnostic not in diagnostics:
            diagnostics.append(diagnostic)

    for effect in effects:
        if effect.state == "unknown" and (effect.kind, effect.effect_id) not in conflict_keys:
            diagnostic = Diagnostic(
                "effect.outcome_unknown", component=effect.kind, evidence_ref=effect.effect_id,
                reconciliation_owner=effect.reconciliation_owner, retry_disposition="reconcile",
            )
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)

    if integrity_diagnostics or any(effect.state == "unknown" for effect in effects):
        outcome = "unknown"
    elif outcome == "succeeded" and any(effect.state == "failed" for effect in effects):
        outcome = "failed"
        diagnostics.append(Diagnostic("effect.failed"))

    if outcome != "succeeded" and not diagnostics:
        diagnostics.append(Diagnostic("operation.incomplete"))
    # Deduplicate equal evidence without collapsing distinct effect references.
    unique = tuple(dict.fromkeys(diagnostics))
    return _ResolvedCompletion(outcome, value, unique)
