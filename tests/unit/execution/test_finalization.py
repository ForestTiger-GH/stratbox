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
    assert len(retained[0].effects) == 1
    assert not hasattr(retained[0].effects, "append")


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


def test_terminal_observation_is_private_and_single_attempt():
    retained = []
    sink = InMemorySink()

    def handler(value, invocation):
        retained.append(invocation)
        assert not hasattr(invocation, "finish")
        return value

    result = run(operation(), "ok", handler, context=ExecutionContext(sink=sink))
    assert result.outcome == "succeeded"
    with pytest.raises(RuntimeError, match="terminal observation"):
        retained[0]._finish("succeeded", None)
    assert len([event for event in sink.events if event.kind == "operation.finished"]) == 1


@pytest.mark.parametrize("effect_state, expected", [
    (None, "failed"), ("confirmed", "failed"), ("unknown", "unknown"),
])
def test_finalizer_constructor_failure_is_classified_before_terminal_event(monkeypatch, effect_state, expected):
    from stratbox.core.execution import runner as module
    original = module.OperationResult
    calls = []

    def inject_validation_error(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise ValueError("synthetic validation failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "OperationResult", inject_validation_error)
    sink = InMemorySink()

    def handler(value, invocation):
        if effect_state is not None:
            invocation.effect(EffectReceipt("storage.write", effect_state, effect_id="effect_X"))
        return value

    result = run(operation(), "ok", handler, context=ExecutionContext(sink=sink))
    assert len(calls) == 2
    assert result.outcome == expected
    assert result.value is None
    assert any(d.code == "internal.error" for d in result.diagnostics)
    assert sink.events[-1].outcome == expected
    assert len([event for event in sink.events if event.kind == "operation.finished"]) == 1


def test_finalization_freezes_input_evidence_even_if_invocation_is_retained():
    from stratbox.shared.evidence import UsedInputReceipt
    retained = []
    receipt = UsedInputReceipt("input", ByteIdentity.of(b"input"), "application/octet-stream", "inline")

    def handler(value, invocation):
        retained.append(invocation)
        invocation.use(receipt)
        return value

    result = run(operation(), "ok", handler)
    assert result.used_inputs == (receipt,)
    assert retained[0].used_inputs == (receipt,)
    with pytest.raises(RuntimeError, match="finalized"):
        retained[0].use(receipt)
    assert result.used_inputs == (receipt,)


def test_representation_accounting_and_computation_receipt_is_independent_of_effects():
    from stratbox.shared.data.representation import Representation
    from stratbox.core.limits import ExecutionBudget

    op = OperationDefinition("test.render", 1, "render-v1", bytes, Representation,
                             possible_effects=frozenset({"storage.write"}))
    payload = Representation("sample.csv", 1, "text/csv", b"x,y\\n1,2\\n")
    purely_computed = run(op, b"seed", lambda req, inv: payload)
    assert purely_computed.outcome == "succeeded"
    assert dict(purely_computed.resources_used)["output_bytes"] == payload.identity.size
    assert purely_computed.computation is not None

    def published(req, inv):
        inv.account_output(payload.identity, key="publish:write_id")
        inv.account_output(payload.identity, key="returned", covered_by="publish:write_id")
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="write_id"))
        return payload

    saved = run(op, b"seed", published, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=payload.identity.size),
    ))
    assert saved.outcome == "succeeded"
    assert dict(saved.resources_used)["output_bytes"] == payload.identity.size
    assert saved.computation is not None
    assert saved.effects[0].state == "confirmed"


def test_same_id_across_different_kinds_keeps_two_unresolved_diagnostics():
    def handler(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="shared"))
        invocation.effect(EffectReceipt("notification.handoff", "unknown", effect_id="shared"))
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "unknown"
    sources = [d.component for d in result.diagnostics if d.code == "effect.outcome_unknown"]
    assert sources == ["storage.write", "notification.handoff"]
    assert len(result.effects) == 2


@pytest.mark.parametrize("kwargs", [
    {"reference": object()},
    {"identity": "not-a-byte-identity"},
    {"identity": []},
])
def test_invalid_effect_identity_or_reference_is_rejected(kwargs):
    with pytest.raises(ValueError):
        EffectReceipt("storage.write", "confirmed", effect_id="effect_1", **kwargs)


def test_effect_view_is_read_only_and_linear_time_for_boolean_reads():
    captured = []

    def handler(value, invocation):
        captured.append(invocation)
        for index in range(100):
            invocation.effect(EffectReceipt("storage.write", "confirmed",
                                            effect_id=f"item_{index}"))
            assert bool(invocation.effects)
            assert len(invocation.effects) == index + 1
        assert not hasattr(invocation.effects, "append")
        return value

    result = run(operation(), "ok", handler)
    assert result.outcome == "succeeded"
    assert len(result.effects) == 100
    assert tuple(captured[0].effects) == result.effects


def test_two_anonymous_unknown_effects_keep_two_diagnostics_without_fake_ids():
    def worker(request, invocation):
        invocation.effect(EffectReceipt("storage.write", "unknown"))
        invocation.effect(EffectReceipt("storage.write", "unknown"))
        return request

    result = run(operation(), "sample", worker)
    assert result.outcome == "unknown"
    unresolved = [d for d in result.diagnostics if d.code == "effect.outcome_unknown"]
    assert len(result.effects) == len(unresolved) == 2
    assert all(d.evidence_ref is None and d.retry_disposition == "none" for d in unresolved)


@pytest.mark.parametrize("state, expected", [
    ("confirmed", "failed"),
    ("failed", "failed"),
    ("unknown", "unknown"),
])
def test_computation_survives_later_publication_error(state, expected):
    from stratbox.shared.identity import ByteIdentity
    computed = ByteIdentity.of(b"prepared-output")

    def worker(request, invocation):
        invocation.record(computed, parameters={"phase": "computed"})
        invocation.effect(EffectReceipt("storage.write", state, effect_id="publish"))
        raise RuntimeError("publishing adapter failed after computation")

    result = run(operation(), "ok", worker)
    assert result.outcome == expected
    assert result.value is None
    assert result.computation is not None
    assert result.computation.output == computed
    assert result.effects[0].state == state


def test_large_diagnostics_are_ordered_and_deduplicated_linearly():
    from stratbox.core.execution.resolution import _WorkCompletion, _resolve_completion
    size = 10_000
    items = tuple(Diagnostic(f"domain.issue_{index}") for index in range(size))
    result = _resolve_completion(operation(), _WorkCompletion(
        "failed", None, items + items[::100],
    ), ())
    assert result.outcome == "failed"
    assert result.diagnostics == items


def test_many_distinct_effects_preserve_order_and_anonymous_multiplicity():
    from stratbox.core.execution.resolution import _WorkCompletion, _resolve_completion
    named = tuple(EffectReceipt("storage.write", "unknown", effect_id=f"receipt_{i}")
                  for i in range(10_000))
    unnamed = (EffectReceipt("storage.write", "unknown"),) * 3
    result = _resolve_completion(
        operation(), _WorkCompletion("succeeded", "ok"), named + unnamed,
    )
    assert result.outcome == "unknown"
    assert len(result.diagnostics) == 10_003
    assert [item.evidence_ref for item in result.diagnostics[:3]] == [
        "receipt_0", "receipt_1", "receipt_2",
    ]
    assert all(item.evidence_ref is None for item in result.diagnostics[-3:])


def test_fallback_normalization_keeps_primary_and_effect_diagnostics(monkeypatch):
    from stratbox.core.execution import runner
    def broken_resolver(*args, **kwargs):
        raise RuntimeError("injected resolution error")
    monkeypatch.setattr(runner, "_resolve_completion", broken_resolver)
    sink = InMemorySink()
    def worker(value, invocation):
        invocation.stage("commit")
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="unknown_1"))
        return Completion(value, "failed", "domain.primary")
    result = run(operation(), "value", worker, context=ExecutionContext(sink=sink))
    assert result.outcome == "unknown"
    assert {d.code for d in result.diagnostics} >= {
        "domain.primary", "effect.outcome_unknown", "internal.error",
    }
    assert all(d.stage == "commit" and d.component and d.reason_class
               for d in result.diagnostics)
    assert sink.events[-1].outcome == "unknown"


def test_computation_is_preserved_when_returned_output_exceeds_budget():
    from stratbox.core.limits import ExecutionBudget
    from stratbox.shared.data.representation import Representation
    blob = Representation("report", 1, "text/csv", b"long-output-data")
    definition = OperationDefinition(
        "test.compute_before_output_admission", 1, "method-1",
        bytes, Representation,
    )
    result = run(definition, b"", lambda request, invocation: blob,
                 context=ExecutionContext(budget=ExecutionBudget(output_bytes=3)))
    assert result.outcome == "failed"
    assert result.value is None
    assert result.computation is not None
    assert result.computation.output == blob.identity
    assert any(item.code == "budget.output_bytes" for item in result.diagnostics)


def test_normalizer_failure_yields_safe_internal_diagnostic(monkeypatch):
    from stratbox.core.execution import runner
    def broken_describe(self, diagnostic, outcome):
        raise RuntimeError("do-not-leak")
    monkeypatch.setattr(runner.Invocation, "describe", broken_describe)
    result = run(operation(), "value",
                 lambda value, invocation: Completion(value, "failed", "domain.error"))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "internal.error"
    assert result.diagnostics[0].stage == "admission"
    assert result.diagnostics[0].component == "internal"
    assert result.diagnostics[0].reason_class == "internal"
    assert "do-not-leak" not in str(result.diagnostics)


def test_same_input_bytes_with_different_roles_remain_distinct():
    from stratbox.shared.evidence import UsedInputReceipt
    identity = ByteIdentity.of(b"same-data")
    def worker(value, invocation):
        first = UsedInputReceipt("baseline", identity, "text/plain", "inline")
        second = UsedInputReceipt("candidate", identity, "text/plain", "inline")
        invocation.use(first)
        invocation.use(second)
        invocation.use(first)
        return value
    result = run(operation(), "value", worker)
    assert result.outcome == "succeeded"
    assert len(result.used_inputs) == 2
    assert [item.role for item in result.used_inputs] == ["baseline", "candidate"]


def test_effect_key_is_kind_qualified_and_validates_public_result_snapshot():
    from stratbox.core.execution import EffectKey, OperationResult, ObservabilitySummary
    from stratbox.core.execution import EffectReceipt
    import pytest
    a = EffectReceipt("storage.write", "confirmed", effect_id="shared")
    b = EffectReceipt("notification.handoff", "unknown", effect_id="shared")
    assert a.key == EffectKey("storage.write", "shared")
    assert b.key == EffectKey("notification.handoff", "shared")
    assert a.key != b.key
    op = OperationDefinition("test.keyed", 1, "m-v1", str, str,
        possible_effects=frozenset({"storage.write", "notification.handoff"}))
    with pytest.raises(ValueError, match="Duplicate identified effect"):
        OperationResult(op, "invocation", "unknown", "ok", (Diagnostic("effect.outcome_unknown"),),
                        (), (a, a), ObservabilitySummary(0, 0))
    legal = OperationResult(op, "invocation", "unknown", "ok",
        (Diagnostic("effect.outcome_unknown"),), (), (a, b),
        ObservabilitySummary(0, 0))
    assert len(legal.effects) == 2
    unnamed = EffectReceipt("storage.write", "unknown")
    independent = OperationResult(op, "invocation", "unknown", "ok",
        (Diagnostic("effect.outcome_unknown"),), (), (unnamed, unnamed),
        ObservabilitySummary(0, 0))
    assert len(independent.effects) == 2


def test_public_result_evidence_rejects_mutable_or_malformed_items():
    from stratbox.core.execution import OperationResult, ObservabilitySummary
    op = operation()
    base = OperationResult(
        op, "invocation", "succeeded", "ok", (), (), (),
        ObservabilitySummary(0, 0),
    )
    for changes in (
        {"effects": []}, {"diagnostics": ["domain.problem"]},
        {"used_inputs": [object()]}, {"observability": object()},
        {"invocation_id": "invalid invocation"},
    ):
        with pytest.raises(ValueError):
            replace(base, **changes)
