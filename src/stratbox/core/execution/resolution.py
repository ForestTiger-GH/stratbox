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
    diagnostics: list[Diagnostic] = []
    seen: set[Diagnostic] = set()

    def add(diagnostic: Diagnostic, *, independent_anonymous: bool = False) -> None:
        """Stable, expected O(1) de-duplication of ordinary diagnostics.

        Anonymous effect observations carry multiplicity, even when identical.
        A separate external effect never acquires a synthetic durable ID.
        """
        if independent_anonymous or diagnostic not in seen:
            diagnostics.append(diagnostic)
        seen.add(diagnostic)

    for item in work.diagnostics:
        add(item)
    # Invalid handler results are qualified before effect precedence.
    invalid_value = value is not None and not isinstance(value, definition.value_type)
    missing_value = outcome in {"succeeded", "partial"} and value is None
    illegal_partial = outcome == "partial" and not definition.partial_allowed
    illegal_cancelled_value = outcome == "cancelled" and value is not None
    if invalid_value or missing_value or illegal_partial or illegal_cancelled_value:
        outcome, value = "failed", None
        add(Diagnostic("internal.error"))

    for item in integrity_diagnostics:
        add(item)

    unknown_effect = False
    failed_effect = False
    for effect in effects:
        if effect.state == "failed":
            failed_effect = True
        if effect.state != "unknown":
            continue
        unknown_effect = True
        if (effect.kind, effect.effect_id) in conflict_keys:
            continue
        add(
            Diagnostic(
                "effect.outcome_unknown", component=effect.kind,
                evidence_ref=effect.effect_id,
                reconciliation_owner=effect.reconciliation_owner,
                retry_disposition="reconcile" if effect.effect_id is not None else "none",
            ),
            independent_anonymous=effect.effect_id is None,
        )

    if integrity_diagnostics or unknown_effect:
        outcome = "unknown"
    elif outcome == "succeeded" and failed_effect:
        outcome = "failed"
        add(Diagnostic("effect.failed"))

    if outcome != "succeeded" and not diagnostics:
        add(Diagnostic("operation.incomplete"))
    return _ResolvedCompletion(outcome, value, tuple(diagnostics))
