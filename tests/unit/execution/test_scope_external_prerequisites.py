"""External ordering controls named acceptance and accepted-value publication."""
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    Call, CommandDefinition, Condition, GraphBody, InputRef, OperationDefinition,
    OutputRef, PortContract, ScenarioDefinition,
)
from stratbox.core.execution.contracts import OperationFailure
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract, DataRole


class DelayedPrerequisite:
    def __init__(self):
        self.entered, self.release = Event(), Event()

    def wait(self):
        self.entered.set()
        assert self.release.wait(5)


def delayed_value(request, invocation):
    invocation.provider("prerequisite").wait()
    if request["fail"]:
        raise OperationFailure("fixture.prerequisite_failed")
    return 3


def catalog(*, fail=False, failure_guard=False):
    number = PortContract(DataContract("prerequisite.number", role=DataRole.EXTRACTS), int)
    command = CommandDefinition("prerequisite.value", __name__ + ":delayed_value",
        outputs={"value": number}, parameters={"fail": fail}, required_capabilities=frozenset({"prerequisite"}))
    source = OperationDefinition("prerequisite.source", GraphBody((
        Call("value", command.capability_id),
    ), {"value": OutputRef("value")}), outputs={"value": number})
    forward = OperationDefinition("prerequisite.forward", GraphBody((), {"value": InputRef("input")}),
        inputs={"input": number}, outputs={"value": number})
    condition = Condition("source", statuses=("failed", "blocked")) if failure_guard else None
    root = ScenarioDefinition("prerequisite.task", GraphBody((
        Call("source", source.capability_id),
        Call("forward", forward.capability_id, {"input": 7}, depends_on=("source",), condition=condition),
    ), {"value": OutputRef("forward")}), outputs={"value": number})
    return CatalogSnapshot((command, source, forward, root))


def forward_facts(journal):
    return tuple(entry.record for entry in journal.facts_source._entries.values()
                 if entry.record.kind == "value.accepted" and entry.record.payload["stage"] == "prerequisite.forward")


@pytest.mark.parametrize("fail", (False, True))
def test_passthrough_fact_waits_for_external_prerequisite_and_rejects_failure(fail):
    prerequisite = DelayedPrerequisite()
    with StrategyBox(capabilities=catalog(fail=fail), providers={"prerequisite": prerequisite},
                     settings=ExecutionSettings(max_workers=1)) as box:
        handle = box.submit(box.prepare("prerequisite.task"))
        assert prerequisite.entered.wait(3)
        deadline = monotonic() + 3
        while handle.scope_states().get("prerequisite.task/forward") != "running" and monotonic() < deadline:
            sleep(0.005)
        assert handle.scope_states()["prerequisite.task/forward"] == "running"
        try:
            assert not forward_facts(box.session.journal)
            with pytest.raises(ValueError, match="acceptance.output_unavailable"):
                handle.output("value")
        finally:
            prerequisite.release.set()
        result = handle.result(5)
        if fail:
            assert result.outcome == "failed"
            assert "value" not in result.outputs
            assert not forward_facts(box.session.journal)
        else:
            assert result.outcome == "succeeded", result.diagnostics
            assert result.output("value") == 7
            assert len(forward_facts(box.session.journal)) == 1
        result.close()


def test_explicit_failure_condition_keeps_its_external_status_exemption():
    prerequisite = DelayedPrerequisite()
    with StrategyBox(capabilities=catalog(fail=True, failure_guard=True), providers={"prerequisite": prerequisite}) as box:
        handle = box.submit(box.prepare("prerequisite.task"))
        assert prerequisite.entered.wait(3)
        prerequisite.release.set()
        result = handle.result(5)
        assert result.outcome == "failed"
        assert result.scopes["prerequisite.task/forward"] == "succeeded"
        assert result.output("value") == 7
        assert len(forward_facts(box.session.journal)) == 1
        result.close()
