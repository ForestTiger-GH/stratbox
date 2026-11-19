"""Output accounting is keyed by obligations, not unrelated effects."""
import pytest

from stratbox.core.execution import (
    Completion, EffectReceipt, ExecutionBudget, ExecutionContext, OperationDefinition, run,
)
from stratbox.core.limits import BudgetMeter, BudgetExceeded
from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import ByteIdentity


OUTPUT = OperationDefinition(
    "test.output_accounting", 1, "m-1", bytes, Representation,
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
