"""Resolution context and pinned bindings survive the public preparation route."""
from dataclasses import replace
import json

import pytest

from stratbox.capabilities.catalog import (
    CatalogSnapshot, MethodDefinition, ProcessingGroup, RecipeDefinition,
)
from stratbox.capabilities.model import (
    Call, CommandDefinition, GraphBody, OperationDefinition, OutputRef,
    ParameterRef, PortContract, ScenarioDefinition,
)
from stratbox.composition import ExecutionPlan, GoalRequest, InvocationRequest, validate_plan
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract


NUMBER = PortContract(DataContract("binding.number"), int)
SELECTION = {"source_id": "source.series", "representation": "csv", "edition": "1"}


def constant(request, invocation):
    return request["value"]


def specialized_catalog():
    command = CommandDefinition("binding.constant", __name__ + ":constant",
        parameters={"value": 0}, outputs={"value": NUMBER})
    operation = OperationDefinition("binding.extract", method_slot="layout",
        parameters={"value": 0}, outputs={"value": NUMBER})
    body = GraphBody((Call("constant", command.capability_id,
        parameters={"value": ParameterRef("value")}),), {"value": OutputRef("constant")})
    methods = tuple(MethodDefinition("binding." + layout, operation.capability_id, body,
        selection={"representation": layout}, group_ids=("binding." + layout,)) for layout in ("csv", "xlsx"))
    groups = tuple(ProcessingGroup("binding." + layout, source_ids=("source.series",),
        representations=(layout,), editions=("1",), methods={operation.capability_id: "binding." + layout},
        defaults={"value": value}) for layout, value in (("csv", 5), ("xlsx", 7)))
    recipe = RecipeDefinition("binding.recipe", "binding.goal", operation.capability_id,
        selection={"source_id": "source.series"})
    scenario = ScenarioDefinition("binding.comparison", GraphBody((
        Call("csv", operation.capability_id, selection={"representation": "csv"}),
        Call("xlsx", operation.capability_id, selection={"representation": "xlsx"}),
    ), {"csv": OutputRef("csv"), "xlsx": OutputRef("xlsx")}), outputs={"csv": NUMBER, "xlsx": NUMBER})
    return CatalogSnapshot((command, operation, scenario), methods=methods, groups=groups, recipes=(recipe,))


def test_selection_reaches_exact_goal_and_nested_call_bindings():
    snapshot = specialized_catalog()
    with StrategyBox(capabilities=snapshot) as box:
        exact_plan = box.prepare(InvocationRequest("binding.extract", selection=SELECTION))
        assert exact_plan.selected_bindings["binding.extract"]["group_id"] == "binding.csv"
        assert exact_plan.selected_bindings["binding.extract"]["selection"] == SELECTION
        assert box.run(exact_plan, timeout=5).output("value") == 5
        assert box.invoke("binding.extract", selection=SELECTION, timeout=5).output("value") == 5
        goal_plan = box.prepare_goal(GoalRequest("binding.goal", selection=SELECTION))
        root_binding = goal_plan.selected_bindings["binding.extract"]
        assert root_binding["recipe_id"] == "binding.recipe"
        assert root_binding["identities"]["recipe"] == snapshot.recipes[0].fingerprint
        assert box.run(goal_plan, timeout=5).output("value") == 5
        comparison = box.invoke("binding.comparison", selection=SELECTION, timeout=5)
        assert comparison.output("csv") == 5
        assert comparison.output("xlsx") == 7
        restored = ExecutionPlan.from_dict(json.loads(json.dumps(goal_plan.to_dict())))
        assert validate_plan(restored, box.operations) is restored


def test_changed_processing_group_or_recipe_rejects_retained_plan():
    snapshot = specialized_catalog()
    with StrategyBox(capabilities=snapshot) as box:
        plan = box.prepare_goal(GoalRequest("binding.goal", selection=SELECTION))
    for updated in (
        replace(snapshot, groups=(replace(snapshot.groups[0], defaults={"value": 100}), snapshot.groups[1])),
        replace(snapshot, recipes=(replace(snapshot.recipes[0], revision="2"),)),
    ):
        with StrategyBox(capabilities=updated) as box:
            with pytest.raises(ValueError):
                box.submit(plan)
