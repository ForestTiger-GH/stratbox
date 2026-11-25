"""Preparation regressions for inherited activation and exact binding replay."""
from dataclasses import replace

import pytest

from stratbox.capabilities.model import (
    CommandDefinition, OperationDefinition, ScenarioDefinition, PortContract,
    GraphBody, Call, InputRef, OutputRef, ParameterRef, Condition,
)
from stratbox.capabilities.catalog import (
    CatalogContribution, CatalogSnapshot, MethodDefinition, ProcessingGroup, RecipeDefinition,
)
from stratbox.composition import prepare_invocation, prepare_goal, GoalRequest, validate_plan
from stratbox.sdk.bootstrap import CapabilityRuntimeCatalog
from stratbox.shared.data.processing import DataContract

FLAG = PortContract(DataContract("audit.flag"),bool)


def flag(request,invocation):
    return request["flag"]


@pytest.fixture
def conditional_catalog():
    command = CommandDefinition("audit.flag",__name__+":flag",parameters={"flag":True},outputs={"value":FLAG})
    operation = OperationDefinition("audit.flag_operation",GraphBody((
        Call("leaf","audit.flag",parameters={"flag":ParameterRef("flag")}),
    ),{"value":OutputRef("leaf")}),parameters={"flag":True},outputs={"value":FLAG})
    child = ScenarioDefinition("audit.child",GraphBody((
        Call("local","audit.flag_operation",parameters={"flag":False}),
        Call("probe","audit.flag_operation",condition=Condition("local",equals=True)),
        Call("effect","audit.flag_operation",condition=Condition("probe",statuses=("skipped",))),
    ),{"value":OutputRef("effect")}),outputs={"value":FLAG})
    parent = ScenarioDefinition("audit.parent",GraphBody((
        Call("parent_guard","audit.flag_operation",parameters={"flag":False}),
        Call("child","audit.child",condition=Condition("parent_guard",equals=True)),
    ),{"value":OutputRef("child")}),outputs={"value":FLAG})
    return CatalogSnapshot((command,operation,child,parent))


def test_nested_local_condition_preserves_parent_guard(conditional_catalog):
    plan = prepare_invocation("audit.parent",conditional_catalog,CapabilityRuntimeCatalog(conditional_catalog))
    leaf = next(task for task in plan.tasks if task.task_id == "audit.parent/child/effect/leaf/work")
    conditions = tuple(getattr(leaf,"conditions",())) or ((leaf.condition,) if leaf.condition else ())
    assert len(conditions) == 2
    assert any("parent_guard" in condition.task for condition in conditions)
    assert any("probe" in condition.task for condition in conditions)


def test_selection_reaches_exact_and_goal_method_resolution():
    command = CommandDefinition("audit.flag",__name__+":flag",parameters={"flag":True},outputs={"value":FLAG})
    operation = OperationDefinition("audit.specialized",method_slot="format",outputs={"value":FLAG})
    method = MethodDefinition("audit.xlsx","audit.specialized",GraphBody((Call("leaf","audit.flag"),),{"value":OutputRef("leaf")}),selection={"format":"xlsx"})
    snapshot = CatalogSnapshot((command,operation),methods=(method,),recipes=(RecipeDefinition("audit.recipe","audit.goal","audit.specialized",selection={"format":"xlsx"}),))
    runtime = CapabilityRuntimeCatalog(snapshot)
    exact = prepare_invocation("audit.specialized",snapshot,runtime,selection={"format":"xlsx"})
    goal = prepare_goal(GoalRequest("audit.goal",selection={"format":"xlsx"}),snapshot,runtime)
    assert exact.selected_bindings["audit.specialized"]["method_id"] == "audit.xlsx"
    assert goal.selected_bindings["audit.specialized"]["method_id"] == "audit.xlsx"
    assert goal.selected_bindings["audit.specialized"]["recipe_id"] == "audit.recipe"


def test_changed_processing_group_invalidates_prepared_plan(conditional_catalog):
    group = ProcessingGroup("audit.group",selection={"format":"xlsx"})
    snapshot = conditional_catalog.overlay(CatalogContribution(groups=(group,)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation("audit.flag_operation",snapshot,runtime,group_id="audit.group")
    changed = replace(group,selection={"format":"csv"})
    updated = replace(snapshot,groups=(changed,))
    with pytest.raises(ValueError,match="binding_changed"):
        validate_plan(plan,CapabilityRuntimeCatalog(updated))


def test_call_selection_override_and_group_defaults_are_pinned():
    command = CommandDefinition("audit.flag",__name__+":flag",parameters={"flag":True},outputs={"value":FLAG})
    operation = OperationDefinition("audit.specialized",method_slot="format",parameters={"flag":True},outputs={"value":FLAG})
    body = GraphBody((Call("leaf","audit.flag",parameters={"flag":ParameterRef("flag")}),),{"value":OutputRef("leaf")})
    methods = (
        MethodDefinition("audit.xlsx","audit.specialized",body,selection={"format":"xlsx"}),
        MethodDefinition("audit.csv","audit.specialized",body,selection={"format":"csv"},defaults={"flag":False}),
    )
    scenario = ScenarioDefinition("audit.selection",GraphBody((
        Call("child","audit.specialized",selection={"format":"csv"}),
    ),{"value":OutputRef("child")}),outputs={"value":FLAG})
    snapshot = CatalogSnapshot((command,operation,scenario),methods=methods)
    plan = prepare_invocation(scenario.capability_id,snapshot,CapabilityRuntimeCatalog(snapshot),selection={"format":"xlsx"})
    binding = plan.selected_bindings["audit.selection/child"]
    assert binding["method_id"] == "audit.csv"
    assert binding["selection"] == {"format":"csv"}
    assert binding["parameters"] == {"flag":False}
    assert binding["supplied_parameters"] == {}
    assert binding["body"]["$type"].endswith(":GraphBody")
    with pytest.raises(TypeError):
        binding["parameters"]["flag"] = True


def test_recipe_revision_and_defaults_are_revalidated(conditional_catalog):
    recipe = RecipeDefinition("audit.recipe","audit.goal","audit.flag_operation",defaults={"flag":False})
    snapshot = conditional_catalog.overlay(CatalogContribution(recipes=(recipe,)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_goal(GoalRequest("audit.goal"),snapshot,runtime)
    binding = plan.selected_bindings["audit.flag_operation"]
    assert binding["parameters"]["flag"] is False
    assert binding["supplied_parameters"] == {}
    updated = replace(snapshot,recipes=(replace(recipe,revision="2"),))
    with pytest.raises(ValueError,match="catalog.binding_changed"):
        validate_plan(plan,CapabilityRuntimeCatalog(updated))


def test_scope_outputs_keep_each_owning_acceptance_boundary(conditional_catalog):
    from stratbox.composition.plan import ScopeOutputRef
    plan = prepare_invocation("audit.parent",conditional_catalog,CapabilityRuntimeCatalog(conditional_catalog))
    public = plan.outputs["value"]
    assert isinstance(public,ScopeOutputRef) and public.scope_id == "audit.parent"
    root = next(scope for scope in plan.scopes if scope.scope_id == public.scope_id)
    assert isinstance(root.outputs["value"],ScopeOutputRef)
    assert root.outputs["value"].scope_id == "audit.parent/child"
    child = next(scope for scope in plan.scopes if scope.scope_id == "audit.parent/child")
    assert child.outputs["value"].scope_id == "audit.parent/child/effect"


def test_map_template_carries_selection_into_dynamic_binding():
    from stratbox.capabilities.model import MapCall
    from stratbox.composition import expand_map_item
    command = CommandDefinition("audit.flag",__name__+":flag",parameters={"flag":True},outputs={"value":FLAG})
    operation = OperationDefinition("audit.specialized",method_slot="format",outputs={"value":FLAG})
    body = GraphBody((Call("leaf","audit.flag"),),{"value":OutputRef("leaf")})
    method = MethodDefinition("audit.csv","audit.specialized",body,selection={"format":"csv"})
    item = ScenarioDefinition("audit.item",GraphBody((Call("specialized","audit.specialized"),),{"value":OutputRef("specialized")}),
                              inputs={"item":FLAG},outputs={"value":FLAG})
    collection = PortContract(FLAG.schema,object,collection=True)
    parent = ScenarioDefinition("audit.map",GraphBody((
        MapCall("items","audit.item",(True,),selection={"format":"csv"}),
    ),{"value":OutputRef("items")}),outputs={"value":collection})
    snapshot = CatalogSnapshot((command,operation,item,parent),methods=(method,))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation(parent.capability_id,snapshot,runtime,selection={"format":"xlsx"})
    task = next(task for task in plan.tasks if task.map is not None)
    assert task.map.body.selection == {"format":"csv"}
    expanded = expand_map_item(plan,task,"0",True,runtime)
    binding = expanded.selected_bindings["audit.map/items/0/specialized"]
    assert binding["selection"] == {"format":"csv"}
    assert binding["method_id"] == "audit.csv"


def test_invocation_and_goal_selection_are_immutable_snapshots():
    from stratbox.composition import InvocationRequest
    selection = {"format":"xlsx","edition":{"allowed":["2026"]}}
    exact = InvocationRequest("audit.flag",selection=selection)
    goal = GoalRequest("audit.goal",selection=selection)
    selection["edition"]["allowed"].append("2027")
    assert exact.selection["edition"]["allowed"] == ("2026",)
    assert goal.selection["edition"]["allowed"] == ("2026",)


def test_full_binding_and_named_promises_roundtrip(conditional_catalog):
    import json
    from stratbox.composition import ExecutionPlan
    runtime = CapabilityRuntimeCatalog(conditional_catalog)
    plan = prepare_invocation("audit.parent",conditional_catalog,runtime)
    restored = ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
    assert restored == plan
    assert validate_plan(restored,runtime) is restored


@pytest.mark.parametrize("mutation",["policy","basis"])
def test_retained_plan_cannot_widen_command_reuse_policy(conditional_catalog,mutation):
    from stratbox.composition.compiler import plan_identity
    runtime = CapabilityRuntimeCatalog(conditional_catalog)
    plan = prepare_invocation("audit.flag_operation",conditional_catalog,runtime)
    task = next(task for task in plan.tasks if task.operation_id is not None)
    if mutation == "policy":
        altered = replace(task,reuse_contract=replace(task.reuse_contract,mutation="exclusive"))
        code = "composition.command_policy_changed"
    else:
        basis = replace(task.reuse_identity,schema_fingerprint="different")
        altered = replace(task,reuse_identity=basis,work_identity=basis.fingerprint)
        code = "composition.work_identity_changed"
    changed = replace(plan,tasks=tuple(altered if item.task_id == task.task_id else item for item in plan.tasks))
    changed = replace(changed,plan_id=plan_identity(changed.definition_id,changed.tasks,changed.outputs,
        changed.scopes,changed.policy,changed.root_kind,changed.selected_bindings))
    with pytest.raises(ValueError,match=code):
        validate_plan(changed,runtime)
