"""Conformance matrix for single-operation outcome/effect finalization.

No network, GitHub Actions, external service or domain-specific heavy extra.
"""
from dataclasses import replace
from threading import Event

import pytest

from stratbox.core.execution import (
    Completion, Diagnostic, EffectReceipt, ExecutionContext, InMemorySink,
    OperationDefinition, OperationFailure, run,
)
from stratbox.shared.identity import ByteIdentity


DECL = frozenset({"storage.write", "storage.remove", "notification.handoff"})


def operation(*, partial_allowed=True, effects=DECL):
    return OperationDefinition(
        "test.execution_finalization", 1, "test-1", str, str,
        possible_effects=effects, partial_allowed=partial_allowed,
    )


def work_result(kind):
    def worker(request, invocation):
        if kind == "cancelled":
            raise OperationFailure("operation.cancelled", outcome="cancelled")
        if kind == "succeeded":
            return request
        return Completion(request, kind, "domain.incomplete")
    return worker


@pytest.mark.parametrize(
    ("work_state", "effect_state", "expected"),
    [
        ("succeeded", None, "succeeded"),
        ("succeeded", "confirmed", "succeeded"),
        ("succeeded", "failed", "failed"),
        ("succeeded", "unknown", "unknown"),
        ("partial", None, "partial"),
        ("partial", "confirmed", "partial"),
        ("partial", "failed", "partial"),
        ("partial", "unknown", "unknown"),
        ("failed", None, "failed"),
        ("failed", "confirmed", "failed"),
        ("failed", "failed", "failed"),
        ("failed", "unknown", "unknown"),
        ("cancelled", None, "cancelled"),
        ("cancelled", "confirmed", "cancelled"),
        ("cancelled", "failed", "cancelled"),
        ("cancelled", "unknown", "unknown"),
        ("unknown", None, "unknown"),
        ("unknown", "confirmed", "unknown"),
        ("unknown", "failed", "unknown"),
        ("unknown", "unknown", "unknown"),
    ],
)
def test_complete_outcome_matrix(work_state, effect_state, expected):
    sink = InMemorySink()

    def handler(value, invocation):
        if effect_state is not None:
            invocation.effect(EffectReceipt("storage.write", effect_state, effect_id="effect_A"))
        return work_result(work_state)(value, invocation)

    result = run(operation(), "sample", handler, context=ExecutionContext(sink=sink))
    assert result.outcome == expected
    assert sink.events[-1].kind == "operation.finished"
    assert sink.events[-1].outcome == result.outcome
    assert len([e for e in sink.events if e.kind == "operation.finished"]) == 1
    assert len(result.effects) == (effect_state is not None)
    if work_state == "cancelled":
        assert result.value is None
    else:
        assert result.value == "sample"
    if expected != "succeeded":
        assert result.diagnostics


def test_failed_effect_from_success_returns_structured_result_before_finished():
    sink = InMemorySink()

    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "failed", effect_id="publication"))
        return value

    result = run(operation(), "safe", handler, context=ExecutionContext(sink=sink))
    assert result.outcome == "failed"
    assert result.value == "safe"
    assert result.diagnostics[-1].code == "effect.failed"
    assert sink.events[-1].outcome == "failed"


def test_anonymous_effects_remain_independent_and_unknown_receipts_are_separate():
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "confirmed"))
        invocation.effect(EffectReceipt("storage.write", "unknown"))
        invocation.effect(EffectReceipt("storage.write", "unknown"))
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "unknown"
    assert [e.state for e in result.effects] == ["confirmed", "unknown", "unknown"]


def test_progressive_qualification_preserves_identity_and_first_position():
    original = EffectReceipt(
        "storage.write", "unknown", effect_id="stable", reference="private/path",
        identity=ByteIdentity.of(b"payload"), stage="commit", guarantee="atomic_create",
        reconciliation_owner="store",
    )

    def handler(value, invocation):
        invocation.effect(original)
        invocation.effect(EffectReceipt("storage.remove", "confirmed", effect_id="other"))
        invocation.effect(replace(original, state="confirmed", stage="verify"))
        invocation.effect(replace(original, state="confirmed", stage="verify"))
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "succeeded"
    assert len(result.effects) == 2
    assert result.effects[0].state == "confirmed"
    assert result.effects[0].stage == "verify"
    assert result.effects[0].reference == "private/path"
    assert result.effects[1].kind == "storage.remove"


def test_unknown_to_failed_is_authoritative_known_failure():
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="stable"))
        invocation.effect(EffectReceipt("storage.write", "failed", effect_id="stable"))
        return value

    result = run(operation(), "value", handler)
    assert result.outcome == "failed"
    assert len(result.effects) == 1 and result.effects[0].state == "failed"


@pytest.mark.parametrize("second", [
    EffectReceipt("storage.write", "failed", effect_id="stable"),
    EffectReceipt("storage.write", "unknown", effect_id="stable"),
    EffectReceipt("storage.write", "confirmed", effect_id="stable", identity=ByteIdentity.of(b"other")),
    EffectReceipt("storage.write", "confirmed", effect_id="stable", reference="private/other"),
    EffectReceipt("storage.write", "confirmed", effect_id="stable", guarantee="weak"),
])
def test_conflicting_receipts_are_sticky_even_if_handler_continues(second):
    first = EffectReceipt(
        "storage.write", "confirmed", effect_id="stable",
        reference="private/original", identity=ByteIdentity.of(b"original"),
        guarantee="verified_commit",
    )

    def handler(value, invocation):
        invocation.effect(first)
        invocation.effect(second)
        invocation.effect(first)  # Cannot erase a detected contradiction.
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "unknown"
    assert result.effects[0].state == "unknown"
    conflict = next(x for x in result.diagnostics if x.code == "effect.receipt_conflict")
    assert conflict.evidence_ref == "stable"
    assert conflict.retry_disposition == "reconcile"
    assert "private/" not in str(result.diagnostics)


def test_failed_to_confirmed_is_a_conflict_not_a_retry():
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "failed", effect_id="stable"))
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="stable"))
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "unknown"
    assert result.effects[0].state == "unknown"


def test_incompatible_partial_is_normalized_before_event():
    sink = InMemorySink()
    result = run(
        operation(partial_allowed=False), "ok",
        lambda value, invocation: Completion(value, "partial", "domain.some_rows"),
        context=ExecutionContext(sink=sink),
    )
    assert result.outcome == "failed"
    assert result.value is None
    assert result.diagnostics[-1].code == "internal.error"
    assert sink.events[-1].outcome == "failed"


@pytest.mark.parametrize("effect_state,expected", [
    ("confirmed", "failed"), ("unknown", "unknown"),
])
def test_invalid_handler_return_preserves_effect_truth(effect_state, expected):
    sink = InMemorySink()

    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", effect_state, effect_id="affected"))
        return 17  # Outside the operation contract.

    result = run(operation(), "ok", handler, context=ExecutionContext(sink=sink))
    assert result.outcome == expected
    assert result.value is None
    assert any(d.code == "internal.error" for d in result.diagnostics)
    assert sink.events[-1].outcome == expected
    assert result.effects[0].state == effect_state


def test_primary_internal_error_and_external_unknown_are_both_preserved():
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "unknown",
                                        effect_id="output", reconciliation_owner="store"))
        raise RuntimeError("private-secret-DO-NOT-LEAK")

    result = run(operation(), "ok", handler)
    assert result.outcome == "unknown"
    codes = [item.code for item in result.diagnostics]
    assert "internal.error" in codes and "effect.outcome_unknown" in codes
    external = next(item for item in result.diagnostics if item.code == "effect.outcome_unknown")
    assert external.retry_disposition == "reconcile"
    assert external.evidence_ref == "output"
    assert external.reconciliation_owner == "store"
    assert not any("DO-NOT-LEAK" in str(item) for item in result.diagnostics)


def test_domain_unknown_without_external_effect_does_not_request_reconciliation():
    result = run(
        operation(), "input",
        lambda value, invocation: Completion(value, "unknown", "source.selection_ambiguous"),
    )
    assert result.outcome == "unknown"
    assert all(item.retry_disposition != "reconcile" for item in result.diagnostics)


def test_multiple_unknown_effects_keep_distinct_reconciliation_references():
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="first"))
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="second"))
        return value

    result = run(operation(), "ok", handler)
    refs = [d.evidence_ref for d in result.diagnostics if d.code == "effect.outcome_unknown"]
    assert refs == ["first", "second"]


def test_undeclared_effect_is_contract_failure_before_false_success():
    result = run(
        operation(effects=frozenset()), "ok",
        lambda value, inv: (inv.effect(EffectReceipt("storage.write", "confirmed")), value)[1],
    )
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "internal.error"


def test_cancel_before_and_after_effect_checkpoints():
    cancelled = Event()
    cancelled.set()
    touched = []
    first = run(
        operation(), "ok", lambda value, inv: touched.append(1) or value,
        context=ExecutionContext(cancellation=cancelled),
    )
    assert first.outcome == "cancelled" and not touched

    cancelled.clear()

    def handler(value, inv):
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="one"))
        cancelled.set()
        inv.check_cancelled()
        return value

    interrupted = run(operation(), "ok", handler, context=ExecutionContext(cancellation=cancelled))
    assert interrupted.outcome == "cancelled"
    assert interrupted.effects[0].state == "confirmed"


def test_late_cancel_after_confirmed_effect_does_not_override_success():
    token = Event()

    def handler(value, inv):
        inv.effect(EffectReceipt("storage.write", "unknown", effect_id="one"))
        token.set()
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="one"))
        return value

    result = run(operation(), "ok", handler, context=ExecutionContext(cancellation=token))
    assert result.outcome == "succeeded"


def test_external_unknown_overrides_accepted_cancellation():
    token = Event()

    def handler(value, inv):
        inv.effect(EffectReceipt("storage.write", "unknown", effect_id="one"))
        token.set()
        inv.check_cancelled()
        return value

    result = run(operation(), "ok", handler, context=ExecutionContext(cancellation=token))
    assert result.outcome == "unknown"
    assert any(d.code == "operation.cancelled" for d in result.diagnostics)


def test_invocation_is_sealed_and_result_receipts_are_snapshotted():
    retained = []

    def handler(value, inv):
        retained.append(inv)
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="one"))
        return value

    result = run(operation(), "ok", handler)
    with pytest.raises(RuntimeError, match="finalized"):
        retained[0].effect(EffectReceipt("storage.write", "failed", effect_id="one"))
    with pytest.raises(RuntimeError, match="finalized"):
        retained[0].stage("late")
    assert result.effects[0].state == "confirmed"
    assert isinstance(retained[0].effects, tuple)


def test_sink_accept_then_raise_is_not_retried_or_business_failure():
    class AcceptThenRaise(InMemorySink):
        def emit(self, event):
            super().emit(event)
            raise OSError("ack lost")

    sink = AcceptThenRaise()
    result = run(operation(), "ok", lambda value, inv: value, context=ExecutionContext(sink=sink))
    assert result.outcome == "succeeded"
    assert result.observability.dropped == 2
    assert len([event for event in sink.events if event.kind == "operation.finished"]) == 1


@pytest.mark.parametrize("state", ["succeeded", "partial", "failed", "cancelled", "unknown"])
def test_observability_bridge_accepts_actual_terminal_event(state):
    from stratbox.core.observability.capture.adapters import record_from_result
    sink = InMemorySink()
    result = run(
        operation(), "ok", work_result(state), context=ExecutionContext(sink=sink),
    )
    last = sink.events[-1]
    summary = record_from_result(result, finished_event=last)
    assert summary.outcome == state
    assert summary.cause_record_ids


def test_operation_descriptor_lists_only_registrable_effects():
    op = OperationDefinition(
        "test.http_source", 1, "m-1", str, str,
        required_capabilities=frozenset({"http"}),
    )
    assert not op.effects
    op2 = operation()
    assert {item.kind for item in op2.effects} == DECL


@pytest.mark.parametrize("params", [
    {"request_type": "str"},
    {"value_type": "str"},
    {"value_type": ()},
    {"required_capabilities": ("http",)},
    {"possible_effects": {"storage.write"}},
    {"partial_allowed": 1},
])
def test_invalid_operation_definition_is_rejected(params):
    kwargs = dict(operation_id="test.invalid", contract_version=1, method_version="m-1",
                  request_type=str, value_type=str)
    kwargs.update(params)
    with pytest.raises(ValueError):
        OperationDefinition(**kwargs)


def test_conflict_does_not_hide_other_kind_with_same_effect_id():
    # The ID namespace for qualifications is (kind, effect_id), not just ID.
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="shared"))
        invocation.effect(EffectReceipt("storage.write", "failed", effect_id="shared"))
        invocation.effect(EffectReceipt("notification.handoff", "unknown", effect_id="shared"))
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "unknown"
    assert sum(x.code == "effect.receipt_conflict" for x in result.diagnostics) == 1
    assert any(x.code == "effect.outcome_unknown" and x.evidence_ref == "shared"
               for x in result.diagnostics)
