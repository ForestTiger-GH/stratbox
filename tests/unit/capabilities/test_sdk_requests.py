"""Public exact requests, local graphs and goals use the common session."""
from stratbox.capabilities.catalog import CatalogContribution, RecipeDefinition
from stratbox.capabilities.commands import MATERIAL_INPUT, MATERIAL
from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.capabilities.model import (
    Call, CascadeDefinition, GraphBody, InputRef, OperationDefinition,
    OutputRef, ScenarioDefinition,
)
from stratbox.composition.requests import GoalRequest, InvocationRequest
from stratbox.sdk import StrategyBox


def material_graphs():
    operation = OperationDefinition("local.material", GraphBody((
        Call("read", "material.read", {"material": InputRef("material")}),
    ), {"value": OutputRef("read")}), inputs={"material": MATERIAL_INPUT}, outputs={"value": MATERIAL})
    scenario = ScenarioDefinition("local.material_task", GraphBody((
        Call("read", operation.capability_id, {"material": InputRef("material")}),
    ), {"value": OutputRef("read")}), inputs={"material": MATERIAL_INPUT}, outputs={"value": MATERIAL})
    cascade = CascadeDefinition("local.material_package", GraphBody((
        Call("task", scenario.capability_id, {"material": InputRef("material")}),
    ), {"value": OutputRef("task")}), inputs={"material": MATERIAL_INPUT}, outputs={"value": MATERIAL})
    return operation, scenario, cascade


def test_exact_goal_and_four_kinds_preserve_the_same_value_and_retention():
    operation, scenario, cascade = material_graphs()
    snapshot = catalog_snapshot().overlay(CatalogContribution(
        definitions=(operation, scenario, cascade),
        recipes=(RecipeDefinition("local.recipe", "local.material_goal", cascade.capability_id),)))
    with StrategyBox(capabilities=snapshot) as box:
        results = []
        for definition in ("material.read", operation, scenario, cascade):
            plan = box.compile(definition, inputs={"material": b"accepted bytes"})
            expected = "command" if isinstance(definition, str) else definition.kind
            assert plan.root_kind == expected
            result = box.run(plan, timeout=5)
            assert result.outcome == "succeeded"
            results.append(result)
        exact = box.run(InvocationRequest("material.read", inputs={"material": b"accepted bytes"}), timeout=5)
        goal = box.invoke(GoalRequest("local.material_goal", inputs={"material": b"accepted bytes"}), timeout=5)
        assert exact.outcome == goal.outcome == "succeeded"
        results.extend((exact, goal))
    identities = {result.output("value").identity for result in results}
    assert len(identities) == 1
    for result in results:
        result.close()


def test_ad_hoc_definition_is_admitted_once_and_addressable_in_the_same_client():
    operation, _, _ = material_graphs()
    with StrategyBox() as box:
        direct = box.invoke(operation, inputs={"material": b"local"}, timeout=5)
        addressed = box.invoke(operation.capability_id, inputs={"material": b"local"}, timeout=5)
        assert direct.outcome == addressed.outcome == "succeeded"
        assert direct.output("value") == addressed.output("value")
        description = box.describe(operation.capability_id)
        assert description["kind"] == "operation"
