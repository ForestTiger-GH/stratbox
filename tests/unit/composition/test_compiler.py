from dataclasses import dataclass, replace
import json
import pytest

from stratbox.composition import (
    CascadeDefinition, CollectSpec, CollectStep, CompositionError, Condition,
    ExecutionPlan, InputRef, MapStep, OperationStep, PlanOutputRef as Ref,
    ScenarioDefinition, ScenarioStep, TemplateDefinition, TemplateSlot,
    bind_template, compile_workflow, definition_from_dict, definition_to_dict,
    expand_map_item,
)
from stratbox.core.execution import OperationDefinition, OperationSemantics, ProcessingStage, InputPort, OutputPort, run
from stratbox.core.execution.handoff import prepare_input
from stratbox.shared.data.processing import DataContract
from stratbox.operations.catalog import OperationCatalog, OperationRef

NUMBER = DataContract("test.number")
TEXT = DataContract("test.text")
NUMBERS = DataContract("test.numbers")


@dataclass(frozen=True)
class Produce:
    value: int


@dataclass(frozen=True)
class Transform:
    value: int
    factor: int = 2


PRODUCE = OperationDefinition("test.produce", "test.produce", Produce, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        outputs=(OutputPort("number", NUMBER),), parameters=("value",),
        required_parameters=("value",), summary="Produce a number."))
TRANSFORM = OperationDefinition("test.transform", "test.transform", Transform, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("number", NUMBER, "value"),), outputs=(OutputPort("number", NUMBER),),
        parameters=("factor",), summary="Transform a number."))
WRONG = replace(TRANSFORM, operation_id="test.wrong", processing=replace(TRANSFORM.processing, inputs=(InputPort("number", TEXT, "value"),)))
WRITE = replace(PRODUCE, operation_id="test.write", possible_effects=frozenset({"file.write"}))


def produce(request, *, context=None):
    return run(PRODUCE, request, lambda req, inv: req.value, context=context)


def transform(request, *, context=None):
    return run(TRANSFORM, request, lambda req, inv: req.value * req.factor, context=context)


@pytest.fixture
def catalog():
    return OperationCatalog(tuple(OperationRef(definition.operation_id,
        __name__ + ":" + ("produce" if definition in (PRODUCE, WRITE) else "transform"), definition=definition)
        for definition in (PRODUCE, TRANSFORM, WRONG, WRITE)))


def chain():
    return ScenarioDefinition("chain", (
        OperationStep("source", "test.produce", parameters={"value": 3}),
        OperationStep("double", "test.transform", inputs={"number": Ref("source", "number")}),
    ), {"answer": Ref("double", "number")})


def test_two_calls_and_plan_identity(catalog):
    plan = compile_workflow(chain(), catalog)
    assert [task.task_id for task in plan.tasks] == ["chain/source", "chain/double"]
    assert plan.tasks[1].dependencies == ("chain/source",)
    assert plan.tasks[1].inputs["number"] == Ref("chain/source", "number")
    assert plan == compile_workflow(chain(), catalog)
    changed = replace(chain(), steps=(replace(chain().steps[0], parameters={"value": 4}), chain().steps[1]))
    assert compile_workflow(changed, catalog).plan_id != plan.plan_id
    assert all(task.method_fingerprint for task in plan.tasks)


def test_same_operation_instances_remain_distinct(catalog):
    scenario = ScenarioDefinition("two", (OperationStep("a", "test.produce", parameters={"value": 1}), OperationStep("b", "test.produce", parameters={"value": 2})))
    assert len(compile_workflow(scenario, catalog).tasks) == 2


def test_nested_scenarios_flatten_and_alias_outputs(catalog):
    scenario = ScenarioDefinition("outer", (
        ScenarioStep("nested", chain()),
        OperationStep("last", "test.transform", inputs={"number": Ref("nested", "answer")}),
    ), {"answer": Ref("last", "number")})
    plan = compile_workflow(scenario, catalog)
    assert len(plan.tasks) == 3
    assert plan.tasks[-1].inputs["number"] == Ref("outer/nested/double", "number")
    assert plan.scopes[1].parent_id == "outer"


def test_cascade_uses_same_compiler(catalog):
    plan = compile_workflow(CascadeDefinition("cascade", (ScenarioStep("one", chain()), ScenarioStep("two", chain())), {"answer": Ref("two", "answer")}), catalog)
    assert len(plan.tasks) == 4
    assert plan.outputs["answer"].task == "cascade/two/double"


def test_selected_output_prunes_unrelated_work(catalog):
    scenario = replace(chain(), steps=(*chain().steps, OperationStep("unrelated", "test.produce", parameters={"value": 5})), outputs={**chain().outputs, "extra": Ref("unrelated", "number")})
    plan = compile_workflow(scenario, catalog, outputs=("answer",))
    assert len(plan.tasks) == 2
    assert set(plan.outputs) == {"answer"}


def test_local_supplied_input_has_no_source_task(catalog):
    scenario = ScenarioDefinition("local", (OperationStep("double", "test.transform", inputs={"number": InputRef("source")}),), {"answer": Ref("double", "number")}, {"source": NUMBER})
    plan = compile_workflow(scenario, catalog, inputs={"source": 7})
    assert len(plan.tasks) == 1
    assert plan.tasks[0].inputs["number"].value == 7


@pytest.mark.parametrize("scenario,code", [
    (ScenarioDefinition("bad", (OperationStep("x", "test.transform"),)), "handoff.input_required"),
    (ScenarioDefinition("bad", (OperationStep("x", "test.produce"),)), "handoff.parameter_required"),
    (ScenarioDefinition("bad", (OperationStep("x", "test.produce", parameters={"value": 1, "unknown": 2}),)), "handoff.parameter_unknown"),
    (ScenarioDefinition("bad", (OperationStep("x", "test.transform", inputs={"number": Ref("missing", "number")}),)), "composition.task_unknown"),
    (ScenarioDefinition("bad", (OperationStep("x", "test.transform", inputs={"number": Ref("x", "number")}),)), "composition.cycle"),
])
def test_rejects_invalid_graphs_before_invocation(catalog, scenario, code):
    with pytest.raises(ValueError, match=code):
        compile_workflow(scenario, catalog)


def test_mismatched_named_contract_rejected(catalog):
    scenario = replace(chain(), steps=(chain().steps[0], replace(chain().steps[1], operation_id="test.wrong")))
    with pytest.raises(CompositionError, match="processing.schema_mismatch"):
        compile_workflow(scenario, catalog)


def test_invalid_output_port_rejected(catalog):
    scenario = replace(chain(), outputs={"answer": Ref("double", "wrong")})
    with pytest.raises(CompositionError, match="composition.output_unknown"):
        compile_workflow(scenario, catalog)


def test_explicit_identical_pure_work_shares(catalog):
    steps = tuple(OperationStep(name, "test.produce", parameters={"value": 1}, share_key="one") for name in ("a", "b"))
    scenario = ScenarioDefinition("shared", steps, {"a": Ref("a", "number"), "b": Ref("b", "number")})
    plan = compile_workflow(scenario, catalog)
    assert len(plan.tasks) == 1
    assert plan.tasks[0].aliases == ("shared/b",)
    assert plan.outputs["a"] == plan.outputs["b"]


def test_share_key_does_not_merge_different_parameters(catalog):
    scenario = ScenarioDefinition("shared", tuple(OperationStep(name, "test.produce", parameters={"value": value}, share_key="one") for name, value in (("a", 1), ("b", 2))))
    assert len(compile_workflow(scenario, catalog).tasks) == 2


def test_effects_cannot_be_shared(catalog):
    with pytest.raises(CompositionError, match="composition.effect_sharing_forbidden"):
        compile_workflow(ScenarioDefinition("effect", (OperationStep("a", "test.write", parameters={"value": 1}, share_key="unsafe"),)), catalog)


def map_scenario():
    body = ScenarioDefinition("body", (OperationStep("double", "test.transform", inputs={"number": InputRef("item")}),), {"number": Ref("double", "number")}, {"item": NUMBER})
    return ScenarioDefinition("mapping", (MapStep("each", body, (1, 2, 3), window=2), CollectStep("join", CollectSpec((Ref("each", "number"),), NUMBERS, NUMBER))), {"values": Ref("join")})


def test_map_retains_template_and_expands_one_item(catalog):
    plan = compile_workflow(map_scenario(), catalog)
    assert len(plan.tasks) == 2
    item = expand_map_item(plan, plan.tasks[0], "2026/01", 4, catalog)
    assert item.tasks[0].task_id == "mapping/each/2026%2F01/double"
    assert item.tasks[0].inputs["number"].value == 4
    assert item.outputs["number"].task == item.tasks[0].task_id


def test_map_requires_explicit_collection(catalog):
    scenario = replace(map_scenario(), steps=(map_scenario().steps[0], OperationStep("bad", "test.transform", inputs={"number": Ref("each", "number")})), outputs={})
    with pytest.raises(CompositionError, match="composition.map_collect_required"):
        compile_workflow(scenario, catalog)


def test_json_codec_roundtrips_plan_and_definition(catalog):
    definition = map_scenario()
    assert definition_from_dict(json.loads(json.dumps(definition_to_dict(definition)))) == definition
    plan = compile_workflow(definition, catalog)
    assert ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict()))) == plan
    with pytest.raises(CompositionError, match="composition.unknown_type"):
        definition_from_dict({"$type": "os.system", "value": "arbitrary"})


def test_conditions_have_explicit_dependencies(catalog):
    scenario = replace(chain(), steps=(chain().steps[0], replace(chain().steps[1], condition=Condition("source", statuses=("succeeded",)))))
    task = compile_workflow(scenario, catalog).tasks[1]
    assert task.condition.task == "chain/source"
    assert task.dependencies == ("chain/source",)


def test_template_substitution_validates_port_contracts(catalog):
    template = TemplateDefinition("method", chain(), (TemplateSlot("transform", "double"),))
    scenario = bind_template(template, {"transform": "test.wrong"})
    with pytest.raises(CompositionError, match="processing.schema_mismatch"):
        compile_workflow(scenario, catalog)


def test_template_fixed_parameter_is_invariant():
    template = TemplateDefinition("method", chain(), (TemplateSlot("transform", "double", {"factor": 2}),))
    with pytest.raises(CompositionError, match="composition.fixed_parameter_conflict"):
        bind_template(template, {}, parameters={"transform": {"factor": 3}})


def test_condition_path_and_equality_are_checked_before_execution(catalog):
    for condition, code in (
        (Condition("source", port="number", field="imaginary", equals=1), "composition.condition_field_unknown"),
        (Condition("source", port="number", equals="one"), "composition.condition_value_type_mismatch"),
    ):
        scenario = replace(chain(), steps=(chain().steps[0], replace(chain().steps[1], condition=condition)))
        with pytest.raises(CompositionError, match=code):
            compile_workflow(scenario, catalog)


def test_retained_plan_readmission_rejects_tampering(catalog):
    from stratbox.composition import validate_plan
    plan = compile_workflow(chain(), catalog)
    assert validate_plan(ExecutionPlan.from_dict(plan.to_dict()), catalog) == plan
    changed = replace(plan, tasks=(replace(plan.tasks[0], parameters={"value": 99}), plan.tasks[1]))
    with pytest.raises(CompositionError, match="composition.plan_identity_mismatch"):
        validate_plan(changed, catalog)


def test_retained_plan_readmission_rejects_stale_method(catalog):
    from stratbox.composition import validate_plan
    plan = compile_workflow(chain(), catalog)
    changed = replace(PRODUCE, method_id="test.changed")
    catalog = OperationCatalog(tuple(replace(ref, definition=changed) if ref.operation_id == PRODUCE.operation_id else ref for ref in catalog.references))
    with pytest.raises(CompositionError, match="composition.method_changed"):
        validate_plan(plan, catalog)


def test_map_method_is_pinned_before_dynamic_expansion(catalog):
    plan = compile_workflow(map_scenario(), catalog)
    changed = replace(TRANSFORM, method_id="test.changed")
    catalog = OperationCatalog(tuple(replace(ref, definition=changed) if ref.operation_id == TRANSFORM.operation_id else ref for ref in catalog.references))
    with pytest.raises(CompositionError, match="composition.method_changed"):
        expand_map_item(plan, plan.tasks[0], "a", 1, catalog)


def test_dynamic_input_does_not_hide_invalid_literal_parameter(catalog):
    scenario = replace(chain(), steps=(chain().steps[0], replace(chain().steps[1], parameters={"factor": "two"})))
    with pytest.raises(CompositionError, match="handoff.parameter_type_mismatch"):
        compile_workflow(scenario, catalog)


def test_independently_cancellable_scopes_do_not_share_owned_tasks(catalog):
    inner = ScenarioDefinition("inner", (OperationStep("one", "test.produce", parameters={"value": 1}, share_key="shared"),), {"value": Ref("one", "number")})
    definition = CascadeDefinition("outer", (ScenarioStep("left", inner), ScenarioStep("right", inner)))
    plan = compile_workflow(definition, catalog)
    assert len(plan.tasks) == 2
    assert {task.scope_id for task in plan.tasks} == {"outer/left", "outer/right"}


def test_scope_expenditure_survives_nested_compilation_and_serialization(catalog):
    inner = replace(chain(), expenditure={"objects": 3})
    definition = CascadeDefinition("outer", (ScenarioStep("nested", inner),), expenditure={"bytes": 100})
    plan = compile_workflow(definition, catalog)
    assert dict(plan.scopes[0].expenditure) == {"bytes": 100}
    assert dict(plan.scopes[1].expenditure) == {"objects": 3}
    assert ExecutionPlan.from_dict(plan.to_dict()) == plan


def test_graph_convenience_operation_requires_an_explicit_scenario():
    from stratbox.operations import operation_catalog
    operations = operation_catalog()
    definition = ScenarioDefinition("opaque", (OperationStep("scan", "frg.scan"),))
    with pytest.raises(CompositionError, match="composition.scenario_required"):
        compile_workflow(definition, operations)


def test_expanded_domain_operation_nests_as_an_ordinary_scenario():
    from stratbox.operations import operation_catalog
    from stratbox.composition.builtins import expand_operation
    from stratbox.domains.frank_rg.publications.contracts import DiscoveryRequest
    operations = operation_catalog()
    expanded = expand_operation("frg.scan", DiscoveryRequest("fixture-directory"))
    definition = ScenarioDefinition("nested", (ScenarioStep("scan", expanded),),
                                    {"selection": Ref("scan", "selections")})
    plan = compile_workflow(definition, operations)
    assert [task.operation_id for task in plan.tasks] == ["frg.discover", "frg.inspect", "frg.select"]
    assert plan.outputs["selection"].task == "nested/scan/select"
    assert all(task.scope_id == "nested/scan" for task in plan.tasks)
