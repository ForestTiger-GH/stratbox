"""Each public named output belongs to its own semantic acceptance boundary."""
import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    AcceptanceContract, Call, CascadeDefinition, CommandDefinition, GraphBody,
    OperationDefinition, OutputRef, PortContract, ScenarioDefinition, SemanticPredicate,
)
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract

NUMBER = PortContract(DataContract("audit.number"), int)
MINIMUM = SemanticPredicate(path="value", operator="minimum", expected=5,
                           code="acceptance.number_below_minimum")


def produce(request, invocation):
    return request["value"]


def catalog():
    command = CommandDefinition("record.produce", __name__ + ":produce", parameters={"value": 3}, outputs={"value": NUMBER})
    operation = OperationDefinition("record.operation", GraphBody((Call("source", command.capability_id),),
        {"value": OutputRef("source")}), outputs={"value": NUMBER})
    scenario = ScenarioDefinition("record.scenario", GraphBody((Call("operation", operation.capability_id),),
        {"value": OutputRef("operation")}), outputs={"value": NUMBER})
    cascade = CascadeDefinition("record.cascade", GraphBody((Call("scenario", scenario.capability_id),),
        {"value": OutputRef("scenario")}), outputs={"value": NUMBER})
    return CatalogSnapshot(definitions=(command, operation, scenario, cascade))


@pytest.mark.parametrize("kind", ("command", "operation", "scenario", "cascade"))
def test_rejected_public_promise_never_exposes_successful_child_value(kind):
    from dataclasses import replace
    from stratbox.capabilities.catalog import CatalogContribution
    snapshot = catalog()
    identity = "record.produce" if kind == "command" else "record." + kind
    definition = replace(snapshot.definition(identity), acceptance=AcceptanceContract(predicates=(MINIMUM,)))
    snapshot = snapshot.overlay(CatalogContribution(definitions=(definition,)), replace_ids=(identity,))
    with StrategyBox(capabilities=snapshot) as box:
        handle = box.submit(box.prepare(identity))
        result = handle.result(5)
        assert result.outcome == "failed"
        assert "value" not in result.outputs
        assert not result.scope_outputs.get(identity)
        with pytest.raises(KeyError):
            result.output("value")
        if kind != "command":
            child = identity + {"operation": "/source", "scenario": "/operation", "cascade": "/scenario"}[kind]
            assert result.scope_outputs[child]["value"] == 3
        result.close()


def test_independent_output_survives_its_siblings_named_rejection():
    from stratbox.capabilities.catalog import CatalogContribution
    root = ScenarioDefinition("record.independent", GraphBody((
        Call("good", "record.operation"), Call("bad", "record.operation"),
    ), {"good": OutputRef("good"), "bad": OutputRef("bad")}),
        outputs={"good": NUMBER, "bad": NUMBER}, acceptance=AcceptanceContract(predicates=(
            SemanticPredicate(path="bad", operator="minimum", expected=5,
                              code="acceptance.bad_rejected"),)))
    snapshot = catalog().overlay(CatalogContribution(definitions=(root,)))
    with StrategyBox(capabilities=snapshot) as box:
        result = box.invoke(root.capability_id, timeout=5)
        assert result.outcome == "failed"
        assert result.output("good") == 3
        assert "bad" not in result.outputs
        assert result.scope_outputs["record.independent/bad"]["value"] == 3
        assert "acceptance.bad_rejected" in result.diagnostics
        result.close()
