"""Output accounting is keyed by obligations, not unrelated effects."""
import pytest

from stratbox.core.execution import (
    Completion, EffectReceipt, ExecutionBudget, ExecutionContext, OperationDefinition, run,
)
from stratbox.core.limits import BudgetMeter, BudgetExceeded
from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import ByteIdentity


OUTPUT = OperationDefinition(
    "test.output_accounting", "m-1", bytes, Representation,
    possible_effects=frozenset({"notification.handoff", "storage.write", "storage.remove"}),
    partial_allowed=True,
)


@pytest.mark.parametrize("effect_state", ["confirmed", "failed", "unknown"])
def test_unrelated_effect_cannot_suppress_returned_output_limit(effect_state):
    blob = Representation("table", 1, "text/csv", b"data" * 128)

    def work(req, invocation):
        invocation.effect(EffectReceipt("notification.handoff", effect_state, effect_id="handoff"))
        return blob

    result = run(OUTPUT, b"source", work, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=10),
    ))
    assert any(d.code == "budget.output_bytes" for d in result.diagnostics)
    assert result.effects[0].state == effect_state
    assert result.outcome == ("unknown" if effect_state == "unknown" else "failed")
    assert dict(result.resources_used).get("output_bytes", 0) == 0


def test_storage_effect_without_accounting_does_not_cover_result():
    blob = Representation("out", 1, "text/csv", b"twenty-byte-content")

    def work(req, invocation):
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        return blob

    result = run(OUTPUT, b"", work, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=blob.identity.size - 1),
    ))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "budget.output_bytes"


def test_two_destinations_same_payload_are_independently_accounted():
    meter = BudgetMeter(ExecutionBudget(output_bytes=10))
    digest = ByteIdentity.of(b"12345")
    meter.account_output("publish:one", digest)
    meter.account_output("publish:two", digest)
    assert meter.used("output_bytes") == 10
    meter.account_output("returned", digest, covered_by="publish:one")
    assert meter.used("output_bytes") == 10
    meter.account_output("publish:one", digest)
    assert len(meter.output_accounting()) == 3


def test_conflicting_output_id_or_unproven_alias_is_rejected():
    meter = BudgetMeter(ExecutionBudget(output_bytes=10))
    first, second = ByteIdentity.of(b"aaa"), ByteIdentity.of(b"bbbb")
    meter.account_output("publish:a", first)
    with pytest.raises(ValueError):
        meter.account_output("publish:a", second)
    with pytest.raises(ValueError):
        meter.account_output("returned", second, covered_by="publish:a")
    with pytest.raises(ValueError):
        meter.account_output("returned", first, covered_by="unknown-key")
    assert meter.used("output_bytes") == 3


@pytest.mark.parametrize("n,allowed", [(0, True), (1, True), (2, False)])
def test_boundary_including_empty_payload(n, allowed):
    meter = BudgetMeter(ExecutionBudget(output_bytes=1))
    digest = ByteIdentity.of(b"x" * n)
    if allowed:
        meter.account_output("returned", digest)
        assert meter.used("output_bytes") == n
    else:
        with pytest.raises(BudgetExceeded):
            meter.account_output("returned", digest)
        assert meter.output_accounting() == ()


def test_explicit_returned_alias_is_not_billed_twice():
    blob = Representation("table", 1, "text/csv", b"123456")

    def work(req, invocation):
        invocation.account_output(blob.identity, key="publish:1")
        invocation.account_output(blob.identity, key="returned", covered_by="publish:1")
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="one"))
        return blob

    result = run(OUTPUT, b"", work, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=len(blob.data)),
    ))
    assert result.outcome == "succeeded"
    assert dict(result.resources_used)["output_bytes"] == len(blob.data)


def test_multiple_outputs_share_same_budget_without_effect_dedup():
    meter = BudgetMeter(ExecutionBudget(output_bytes=6))
    meter.account_output("render:a", ByteIdentity.of(b"aaa"))
    with pytest.raises(BudgetExceeded):
        meter.account_output("render:b", ByteIdentity.of(b"bbbb"))
    assert meter.used("output_bytes") == 3


def test_repeat_claim_requires_identical_coverage_and_output_identity():
    meter = BudgetMeter(ExecutionBudget(output_bytes=20))
    blob = ByteIdentity.of(b"contents")
    meter.account_output("publish:one", blob)
    meter.account_output("returned", blob, covered_by="publish:one")
    meter.account_output("returned", blob, covered_by="publish:one")
    with pytest.raises(ValueError, match="Conflicting"):
        meter.account_output("returned", blob)
    meter.ensure_returned_output(blob)
    assert meter.used("output_bytes") == blob.size


def test_ensure_returned_output_rejects_mismatched_published_alias():
    meter = BudgetMeter(ExecutionBudget(output_bytes=20))
    a, b = ByteIdentity.of(b"data"), ByteIdentity.of(b"different")
    meter.account_output("publish:a", a)
    meter.account_output("returned", a, covered_by="publish:a")
    with pytest.raises(ValueError, match="returned output identity"):
        meter.ensure_returned_output(b)
    assert meter.used("output_bytes") == a.size


def test_retry_same_output_key_is_one_logical_obligation():
    meter = BudgetMeter(ExecutionBudget(output_bytes=4))
    identity = ByteIdentity.of(b"1234")
    meter.account_output("publish:same", identity)
    meter.account_output("publish:same", identity)
    assert meter.used("output_bytes") == 4
    # A different published destination is an independent obligation.
    with pytest.raises(BudgetExceeded):
        meter.account_output("publish:other", identity)


@pytest.mark.parametrize(("outcome", "reason"), [
    ("failed", "domain.failed"), ("unknown", "domain.ambiguous"),
    ("partial", "domain.partial"),
])
def test_incomplete_work_output_is_budgeted_and_diagnostics_are_retained(outcome, reason):
    blob = Representation("table", 1, "text/csv", b"x" * 33)
    def worker(request, invocation):
        return Completion(blob, outcome, reason)
    result = run(OUTPUT, b"", worker, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=1),
    ))
    assert result.value is None
    assert result.outcome == ("unknown" if outcome == "unknown" else "failed")
    assert {d.code for d in result.diagnostics} >= {reason, "budget.output_bytes"}
    assert result.computation is not None
    assert result.computation.output == blob.identity
    assert not result.effects


@pytest.mark.parametrize("outcome", ["failed", "unknown"])
def test_incomplete_returned_output_exact_limit_and_zero_boundaries(outcome):
    empty = Representation("table", 1, "text/csv", b"")
    content = Representation("table", 1, "text/csv", b"12")
    for blob, allowed in ((empty, 0), (content, 2)):
        result = run(OUTPUT, b"", lambda req, inv: Completion(blob, outcome, "domain.reason"),
                     context=ExecutionContext(budget=ExecutionBudget(output_bytes=allowed)))
        assert result.outcome == outcome
        assert result.value is blob
        assert dict(result.resources_used)["output_bytes"] == allowed
    rejection = run(OUTPUT, b"", lambda req, inv: Completion(content, outcome, "domain.reason"),
                    context=ExecutionContext(budget=ExecutionBudget(output_bytes=0)))
    assert rejection.value is None
    assert rejection.outcome == outcome
    assert {d.code for d in rejection.diagnostics} >= {"domain.reason", "budget.output_bytes"}


def test_output_refusal_keeps_unresolved_external_effect_and_computation():
    blob = Representation("table", 1, "text/csv", b"x" * 40)
    def worker(req, invocation):
        invocation.effect(EffectReceipt(
            "notification.handoff", "unknown", effect_id="h1",
            reconciliation_owner="consumer",
        ))
        return Completion(blob, "unknown", "domain.ambiguous")
    result = run(OUTPUT, b"", worker, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=1),
    ))
    assert result.outcome == "unknown"
    assert result.value is None
    assert len(result.effects) == 1 and result.effects[0].state == "unknown"
    assert {d.code for d in result.diagnostics} >= {
        "domain.ambiguous", "budget.output_bytes", "effect.outcome_unknown",
    }
    assert result.computation is not None


def test_returned_output_supported_wrapper_is_checked_for_failed():
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class Wrapper:
        representation: Representation
    wrapper = Wrapper(Representation("table", 1, "text/csv", b"12345"))
    operation = OperationDefinition("test.output_wrapper", "method-1", bytes, Wrapper)
    result = run(operation, b"", lambda req, inv: Completion(wrapper, "failed", "domain.failed"),
                 context=ExecutionContext(budget=ExecutionBudget(output_bytes=3)))
    assert result.outcome == "failed" and result.value is None
    assert {d.code for d in result.diagnostics} == {"domain.failed", "budget.output_bytes"}
    assert result.computation is not None


def test_output_refusal_after_confirmed_effect_does_not_erase_receipt():
    blob = Representation("table", 1, "text/csv", b"x" * 80)
    def worker(req, invocation):
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="write_1"))
        return Completion(blob, "failed", "domain.publication_failed")
    result = run(OUTPUT, b"", worker, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=1),
    ))
    assert result.outcome == "failed" and result.value is None
    assert result.effects[0].state == "confirmed"
    assert {d.code for d in result.diagnostics} == {"domain.publication_failed", "budget.output_bytes"}
