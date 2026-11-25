"""Subscriptions consume accepted-output and completion evidence independently."""
import json

import pytest

from stratbox.capabilities.catalog import CatalogContribution
from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.capabilities.model import (
    Call, CommandDefinition, GraphBody, OperationDefinition, OutputRef, ScenarioDefinition,
)
from stratbox.core.execution import OperationFailure
from stratbox.core.notifications import CapabilitySelector
from stratbox.sdk import StrategyBox
from .test_capability_subscriptions import definitions, runtime_for
from .test_required_notification import Inbox


def fail(request, invocation):
    raise OperationFailure("fixture.intentional_failure")


@pytest.mark.parametrize("completed", (False, True))
def test_failed_parent_completion_and_accepted_useful_output_have_distinct_journal_meaning(completed):
    declared = definitions()
    number = declared[0].outputs["value"]
    broken = CommandDefinition("semantics.fail", __name__ + ":fail", outputs={"value": number})
    bad = OperationDefinition("semantics.bad", GraphBody((Call("fail", broken.capability_id),),
        {"value": OutputRef("fail")}), outputs={"value": number})
    parent = ScenarioDefinition("semantics.parent", GraphBody((
        Call("good", "subscription.operation"), Call("bad", bad.capability_id),
    ), {"good": OutputRef("good"), "bad": OutputRef("bad")}), outputs={"good": number, "bad": number})
    snapshot = catalog_snapshot().overlay(CatalogContribution(definitions=(*declared, broken, bad, parent)))
    selector = CapabilitySelector(parent.capability_id, "scenario", output_name=None if completed else "good")
    inbox = Inbox()
    with StrategyBox(capabilities=snapshot) as box:
        _, key = runtime_for(box, inbox, selector=selector, completed=completed)
        result = box.invoke(parent.capability_id, timeout=5)
        assert result.outcome == "failed" and result.output("good") == 11
        notified = box.invoke("notify.required" if completed else "notify.accepted",
            parameters={"key": key, "source_run_id": result.run_id}, timeout=5)
        assert notified.outcome == "succeeded", notified.diagnostics
        assert len(inbox.calls) == 1
        payload = json.loads(inbox.calls[0].intent.envelope_bytes)["data"]
        if completed:
            assert payload["outcome"] == "failed" and "output_name" not in payload
        else:
            assert payload["output_name"] == "good" and "outcome" not in payload
        result.close()
        notified.close()


def test_topic_specific_operation_rejects_mismatch_before_advancing_subscription():
    declared = definitions()
    snapshot = catalog_snapshot().overlay(CatalogContribution(definitions=declared))
    inbox = Inbox()
    with StrategyBox(capabilities=snapshot) as box:
        runtime, key = runtime_for(box, inbox, selector=CapabilitySelector("subscription.command", "command"), completed=True)
        result = box.invoke("subscription.command", timeout=5)
        before = runtime.state.get_checkpoint(key)
        mismatch = box.invoke("notify.accepted", parameters={"key": key, "source_run_id": result.run_id}, timeout=5)
        assert mismatch.outcome == "failed"
        assert runtime.state.get_checkpoint(key) == before and not inbox.calls
        generic = box.invoke("notify.required", parameters={"key": key, "source_run_id": result.run_id}, timeout=5)
        assert generic.outcome == "succeeded", generic.diagnostics
        assert len(inbox.calls) == 1
        result.close()
        mismatch.close()
        generic.close()
