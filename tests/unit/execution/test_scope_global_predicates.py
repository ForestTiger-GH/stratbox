"""Scope predicates over output maps wait for every relevant named output."""
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    AcceptanceContract, Call, CommandDefinition, GraphBody, OperationDefinition,
    OutputRef, ParameterRef, PortContract, ScenarioDefinition, SemanticPredicate,
)
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract


class DelayedOutput:
    def __init__(self):
        self.entered, self.release = Event(), Event()

    def wait(self):
        self.entered.set()
        assert self.release.wait(5)


def value(request, invocation):
    if request["wait"]:
        invocation.provider("delayed_output").wait()
    return request["value"]


def test_global_predicate_cannot_accept_a_partial_map_then_reject_it():
    number = PortContract(DataContract("scope.number"), int)
    command = CommandDefinition("scope.value", __name__ + ":value", outputs={"value": number},
        parameters={"value": 0, "wait": False}, required_capabilities=frozenset({"delayed_output"}))
    operation = OperationDefinition("scope.operation", GraphBody((
        Call("value", command.capability_id, parameters={"value": ParameterRef("value"), "wait": ParameterRef("wait")}),
    ), {"value": OutputRef("value")}), outputs={"value": number}, parameters={"value": 0, "wait": False})
    scenario = ScenarioDefinition("scope.pair", GraphBody((
        Call("left", operation.capability_id, parameters={"value": 1}),
        Call("right", operation.capability_id, parameters={"value": 2, "wait": True}),
    ), {"left": OutputRef("left"), "right": OutputRef("right")}), outputs={"left": number, "right": number},
        acceptance=AcceptanceContract(predicates=(SemanticPredicate("", "equals", {"left": 1}),)))
    delayed = DelayedOutput()
    with StrategyBox(capabilities=CatalogSnapshot((command, operation, scenario)),
                     providers={"delayed_output": delayed}, settings=ExecutionSettings(max_workers=2)) as box:
        handle = box.submit(box.prepare(scenario.capability_id))
        assert delayed.entered.wait(3)
        until = monotonic() + 3
        while handle.scope_states().get("scope.pair/left") != "succeeded" and monotonic() < until:
            sleep(0.005)
        assert handle.scope_states()["scope.pair/left"] == "succeeded"
        try:
            with pytest.raises(ValueError, match="acceptance.output_unavailable"):
                handle.output("left")
        finally:
            delayed.release.set()
        result = handle.result(5)
        assert result.outcome == "failed"
        assert "left" not in result.outputs
        assert "right" not in result.outputs
        assert result.scope_outputs["scope.pair/left"]["value"] == 1
        result.close()
