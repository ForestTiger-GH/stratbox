"""Output closure, scope boundaries and exact identities of canonical calls."""
from dataclasses import replace
import json
import pytest

from stratbox.capabilities.model import (
    CommandDefinition, OperationDefinition, ScenarioDefinition, CascadeDefinition,
    GraphBody, Call, InputRef, OutputRef, ParameterRef, PortContract,
    AcceptanceContract, SemanticPredicate,
)
from stratbox.capabilities.catalog import CatalogSnapshot, CatalogContribution, RecipeDefinition
from stratbox.composition import prepare_invocation, prepare_goal, GoalRequest, ExecutionPlan, validate_plan
from stratbox.sdk.bootstrap import CapabilityRuntimeCatalog
from stratbox.shared.data.processing import DataContract

NUMBER = PortContract(DataContract("test.number"),int)


def constant(values,invocation):
    return values["value"]


def scale(values,invocation):
    return values["number"] * values["factor"]


@pytest.fixture
def snapshot():
    const = CommandDefinition("number.constant",__name__+":constant",outputs={"value":NUMBER},parameters={"value":0})
    multiply = CommandDefinition("number.scale",__name__+":scale",inputs={"number":NUMBER},outputs={"value":NUMBER},parameters={"factor":2})
    op = OperationDefinition("calculate.double",GraphBody((
        Call("constant","number.constant",parameters={"value":ParameterRef("value")}),
        Call("scale","number.scale",inputs={"number":OutputRef("constant")}),
    ),{"value":OutputRef("scale")}),outputs={"value":NUMBER},parameters={"value":0})
    return CatalogSnapshot((const,multiply,op))


def test_cross_operation_command_reuse_preserves_acceptance_scopes(snapshot):
    scenario = ScenarioDefinition("two.doubles",GraphBody((
        Call("left","calculate.double",parameters={"value":3}),
        Call("right","calculate.double",parameters={"value":3}),
    ),{"left":OutputRef("left"),"right":OutputRef("right")}),outputs={"left":NUMBER,"right":NUMBER})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(scenario,)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation(scenario.capability_id,snapshot,runtime)
    commands = [task for task in plan.tasks if task.operation_id]
    assert len(commands) == 4
    assert all(not task.aliases for task in commands)
    assert len([scope for scope in plan.scopes if scope.kind == "operation"]) == 2
    assert plan.outputs["left"] != plan.outputs["right"]
    assert plan.logical_to_physical[plan.outputs["left"].task] == plan.logical_to_physical[plan.outputs["right"].task]
    assert len([task for task in plan.tasks if task.acceptance_scope]) == 3
    assert plan.explain()["physical_work_count"] == 2
    assert plan.explain()["logical_use_count"] == 4
    assert validate_plan(plan,runtime) is plan
    restored = ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
    assert restored == plan
    assert validate_plan(restored,runtime) is restored


def test_consumer_depends_on_operation_acceptance(snapshot):
    first = ScenarioDefinition("consumer",GraphBody((
        Call("initial","calculate.double",parameters={"value":2}),
        Call("later","calculate.double",parameters={"value":OutputRef("initial")}),
    ),{"value":OutputRef("later")}),outputs={"value":NUMBER})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(first,)))
    plan = prepare_invocation(first.capability_id,snapshot,CapabilityRuntimeCatalog(snapshot))
    later = next(task for task in plan.tasks if task.task_id == "consumer/later/constant/work")
    assert "consumer/initial/accept" in later.dependencies


def test_unused_branch_requires_no_input_or_provider(snapshot):
    solver = CommandDefinition("solver.solve",__name__+":scale",inputs={"number":NUMBER},outputs={"value":NUMBER},required_capabilities=frozenset({"solver"}))
    solver_op = OperationDefinition("calculate.solve",GraphBody((Call("solver","solver.solve",inputs={"number":InputRef("model")}),),{"value":OutputRef("solver")}),inputs={"model":NUMBER},outputs={"value":NUMBER})
    scenario = ScenarioDefinition("preview",GraphBody((
        Call("render","calculate.double",parameters={"value":4}),
        Call("solve","calculate.solve",inputs={"model":InputRef("model")}),
    ),{"preview":OutputRef("render"),"solved":OutputRef("solve")}),inputs={"model":NUMBER},outputs={"preview":NUMBER,"solved":NUMBER})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(solver,solver_op,scenario)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation("preview",snapshot,runtime,outputs=("preview",))
    assert all(task.operation_id != "solver.solve" for task in plan.tasks)
    assert "solver.solve" not in runtime._definitions
    with pytest.raises(ValueError,match="composition.input_required"):
        prepare_invocation("preview",snapshot,runtime)


def test_required_effect_is_an_independent_closure_root(snapshot):
    save_command = CommandDefinition("store.save",__name__+":constant",outputs={"value":NUMBER},parameters={"value":0},effects=frozenset({"file.write"}))
    save_operation = OperationDefinition("save.value",GraphBody((Call("commit","store.save",parameters={"value":ParameterRef("value")}),),{"value":OutputRef("commit")},required_effects=("commit",)),outputs={"value":NUMBER},parameters={"value":0},effects=frozenset({"file.write"}))
    scenario = ScenarioDefinition("deliver",GraphBody((
        Call("view","calculate.double",parameters={"value":7}),
        Call("save","save.value",parameters={"value":OutputRef("view")}),
    ),{"value":OutputRef("view"),"receipt":OutputRef("save")},required_effects=("save",)),outputs={"value":NUMBER,"receipt":NUMBER})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(save_command,save_operation,scenario)))
    plan = prepare_invocation("deliver",snapshot,CapabilityRuntimeCatalog(snapshot),outputs=("value",))
    assert any(task.operation_id == "store.save" for task in plan.tasks)
    root = next(scope for scope in plan.scopes if scope.parent_id is None)
    assert root.required_effects == ("deliver/save/accept",)
    assert set(plan.outputs) == {"value"}


def test_retained_value_stops_upstream_expansion(snapshot):
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation("calculate.double",snapshot,runtime,supplied_outputs={"value":12})
    assert len(plan.tasks) == 1 and plan.tasks[0].acceptance_scope == "calculate.double"
    assert plan.outputs["value"] == 12
    assert not runtime._definitions


def test_local_definition_and_goal_use_same_lowering(snapshot):
    local = ScenarioDefinition("local.preview",GraphBody((Call("double","calculate.double",parameters={"value":8}),),{"value":OutputRef("double")}),outputs={"value":NUMBER})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(local,),recipes=(RecipeDefinition("preview.recipe","preview.goal","local.preview"),)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    exact = prepare_invocation("local.preview",snapshot,runtime)
    goal = prepare_goal(GoalRequest("preview.goal"),snapshot,runtime)
    assert exact == goal
    temporary = replace(local,capability_id="temporary.preview")
    assert prepare_invocation(temporary,snapshot,runtime).definition_id == temporary.capability_id


def test_changed_definition_rejects_retained_plan(snapshot):
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation("calculate.double",snapshot,runtime)
    changed = replace(snapshot.definition("calculate.double"),revision="2")
    updated = snapshot.overlay(CatalogContribution(definitions=(changed,)),replace_ids=(changed.capability_id,))
    with pytest.raises(ValueError,match="composition.definition_changed"):
        validate_plan(plan,CapabilityRuntimeCatalog(updated))


def test_plan_codec_rejects_unrecognized_versions(snapshot):
    plan = prepare_invocation("calculate.double",snapshot,CapabilityRuntimeCatalog(snapshot))
    encoded = plan.to_dict()
    encoded["version"] = 2
    with pytest.raises(ValueError,match="composition.unsupported_plan_format"):
        ExecutionPlan.from_dict(encoded)


_EXTERNAL_OFFSET = 0


def external_with_state(values,invocation):
    return values["value"] + _EXTERNAL_OFFSET


def test_explicit_local_method_tracks_consumed_external_state(monkeypatch):
    command = CommandDefinition("local.stateful",__name__+":external_with_state",outputs={"value":NUMBER},parameters={"value":1})
    snapshot = CatalogSnapshot((command,))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation(command.capability_id,snapshot,runtime)
    monkeypatch.setattr(__import__(__name__),"_EXTERNAL_OFFSET",3)
    with pytest.raises(ValueError,match="composition.method_changed"):
        validate_plan(plan,runtime)


def test_canonical_map_collect_uses_one_worker_and_pinned_template(snapshot):
    from stratbox.capabilities.model import MapCall,CollectCall
    from stratbox.core.execution.session import ExecutionSession,ExecutionSettings
    collection = PortContract(DataContract("test.numbers"),tuple,collection=True)
    operation = OperationDefinition("calculate.scale",GraphBody((
        Call("scale","number.scale",inputs={"number":InputRef("number")}),
    ),{"value":OutputRef("scale")}),inputs={"number":NUMBER},outputs={"value":NUMBER})
    item = ScenarioDefinition("item.scenario",GraphBody((
        Call("calculate","calculate.scale",inputs={"number":InputRef("item")}),
    ),{"value":OutputRef("calculate")}),inputs={"item":NUMBER},outputs={"value":NUMBER})
    mapped = ScenarioDefinition("mapped.scenario",GraphBody((
        MapCall("items","item.scenario",(1,2,3),window=2,max_items=3),
        CollectCall("collected",(OutputRef("items"),),collection,NUMBER),
    ),{"value":OutputRef("collected")}),outputs={"value":collection})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(operation,item,mapped)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation(mapped.capability_id,snapshot,runtime)
    assert validate_plan(plan,runtime) is plan
    restored = ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
    assert restored == plan
    with ExecutionSession(runtime,settings=ExecutionSettings(max_workers=1,map_window=2)) as session:
        result = session.submit(plan).result(timeout=5)
        assert result.outcome == "succeeded",result.diagnostics
        assert result.output("value") == (2,4,6)
        assert all(state == "succeeded" for state in result.scopes.values())
        result.close()


def test_nested_canonical_maps_complete_with_one_worker(snapshot):
    from stratbox.capabilities.model import MapCall,CollectCall
    from stratbox.core.execution.session import ExecutionSession,ExecutionSettings
    numbers = PortContract(DataContract("test.numbers"),tuple,collection=True)
    operation = OperationDefinition("calculate.scale",GraphBody((
        Call("scale","number.scale",inputs={"number":InputRef("number")}),
    ),{"value":OutputRef("scale")}),inputs={"number":NUMBER},outputs={"value":NUMBER})
    item = ScenarioDefinition("item.scenario",GraphBody((
        Call("calculate","calculate.scale",inputs={"number":InputRef("item")}),
    ),{"value":OutputRef("calculate")}),inputs={"item":NUMBER},outputs={"value":NUMBER})
    inner = ScenarioDefinition("inner.scenario",GraphBody((
        MapCall("items","item.scenario",InputRef("item"),window=1),
        CollectCall("collected",(OutputRef("items"),),numbers,NUMBER),
    ),{"value":OutputRef("collected")}),inputs={"item":numbers},outputs={"value":numbers})
    nested = PortContract(DataContract("test.nested-numbers"),tuple,collection=True)
    outer = ScenarioDefinition("outer.scenario",GraphBody((
        MapCall("items","inner.scenario",((1,2),(3,4)),window=1),
        CollectCall("collected",(OutputRef("items"),),nested,numbers),
    ),{"value":OutputRef("collected")}),outputs={"value":nested})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(operation,item,inner,outer)))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation(outer.capability_id,snapshot,runtime)
    with ExecutionSession(runtime,settings=ExecutionSettings(max_workers=1,map_window=1)) as session:
        result = session.submit(plan).result(timeout=5)
        assert result.outcome == "succeeded",result.diagnostics
        assert result.output("value") == ((2,4),(6,8))
        result.close()
