"""Dynamic control selectors resolve graph promises before specialization."""
from dataclasses import replace
import json

import pytest

from stratbox.capabilities.catalog import (
    CatalogSnapshot,MethodDefinition,ProfileDefinition,ProcessingGroup,ReferenceDefinition,
)
from stratbox.capabilities.model import (
    CommandDefinition,OperationDefinition,ScenarioDefinition,GraphBody,Call,MapCall,CollectCall,
    InputRef,OutputRef,ParameterRef,PortContract,
)
from stratbox.composition import ExecutionPlan,expand_map_item,prepare_invocation,validate_plan
from stratbox.composition.compiler import plan_identity
from stratbox.core.execution.handoff import prepare_input
from stratbox.sdk.bootstrap import CapabilityRuntimeCatalog
from stratbox.shared.data.processing import DataContract

FORMAT = PortContract(DataContract("dynamic.format"),str)
ITEM = PortContract(DataContract("dynamic.item"),bool)
RESULT = PortContract(DataContract("dynamic.result"),tuple)


def emit_format(request,invocation):
    return request["format"]


def capture_identities(request,invocation):
    return tuple((key,value) for key,value in invocation.context.binding_identities
                 if key in {"method","profile"} or key.startswith("reference:"))


@pytest.fixture
def catalog():
    emitter = CommandDefinition("dynamic.format",__name__+":emit_format",parameters={"format":"csv"},outputs={"value":FORMAT})
    format_operation = OperationDefinition("dynamic.format_operation",GraphBody((
        Call("emit","dynamic.format",parameters={"format":ParameterRef("format")}),
    ),{"value":OutputRef("emit")}),parameters={"format":"csv"},outputs={"value":FORMAT})
    capture = CommandDefinition("dynamic.capture",__name__+":capture_identities",parameters={"profile":{}},
                                outputs={"value":RESULT})
    interpreted = OperationDefinition("dynamic.interpret",method_slot="interpretation",inputs={"item":ITEM},
                                      parameters={"profile":{}},outputs={"value":RESULT})
    method = MethodDefinition("dynamic.csv_method","dynamic.interpret",GraphBody((
        Call("capture","dynamic.capture",parameters={"profile":ParameterRef("profile")}),
    ),{"value":OutputRef("capture")}),selection={"format":"csv"},reference_ids=("dynamic.reference",))
    profile = ProfileDefinition("dynamic.csv_profile",{"edition":"2026"},method_id=method.method_id,
                                group_id="dynamic.csv_group",reference_ids=("dynamic.reference",))
    group = ProcessingGroup("dynamic.csv_group",selection={"format":"csv"},
        methods={interpreted.capability_id:method.method_id},profiles={interpreted.capability_id:profile.profile_id})
    item = ScenarioDefinition("dynamic.item_scenario",GraphBody((
        Call("interpret","dynamic.interpret",inputs={"item":InputRef("item")}),
    ),{"value":OutputRef("interpret")}),inputs={"item":ITEM},outputs={"value":RESULT})
    collection = PortContract(DataContract("dynamic.results"),tuple,collection=True)
    root = ScenarioDefinition("dynamic.map",GraphBody((
        Call("format","dynamic.format_operation"),
        MapCall("items",item.capability_id,(True,),selection={"format":OutputRef("format")}),
        CollectCall("collected",(OutputRef("items"),),collection,RESULT),
    ),{"value":OutputRef("collected")}),outputs={"value":collection})
    return CatalogSnapshot((emitter,format_operation,capture,interpreted,item,root),methods=(method,),
        profiles=(profile,),groups=(group,),references=(ReferenceDefinition("dynamic.reference","2026","reference-edition-2026"),))


def test_graph_selector_is_resolved_before_dynamic_method_selection(catalog):
    runtime = CapabilityRuntimeCatalog(catalog)
    plan = prepare_invocation("dynamic.map",catalog,runtime)
    task = next(task for task in plan.tasks if task.map)
    selected = task.map.body.selection["format"]
    prepared_selector = prepare_input("csv",FORMAT.schema)
    def resolve(value):
        if value == selected:
            return prepared_selector
        if isinstance(value,dict):
            return {key:resolve(item) for key,item in value.items()}
        from collections.abc import Mapping
        if isinstance(value,Mapping):
            return {key:resolve(item) for key,item in value.items()}
        return value
    expanded = expand_map_item(plan,task,"0",True,runtime,resolve_value=resolve)
    binding = expanded.selected_bindings["dynamic.map/items/0/interpret"]
    direct = prepare_invocation("dynamic.interpret",catalog,runtime,inputs={"item":True},selection={"format":"csv"})
    assert binding["selection"] == {"format":"csv"}
    assert binding["identities"] == direct.selected_bindings["dynamic.interpret"]["identities"]
    assert binding["method_id"] == "dynamic.csv_method"
    assert binding["profile_id"] == "dynamic.csv_profile"
    from stratbox.capabilities.model.definitions import declaration_fingerprint
    assert binding["identities"]["reference:dynamic.reference"] == declaration_fingerprint(catalog.reference("dynamic.reference"))
    assert validate_plan(expanded,runtime) is expanded


def test_symbolic_selector_requires_explicit_value_resolution(catalog):
    runtime = CapabilityRuntimeCatalog(catalog)
    plan = prepare_invocation("dynamic.map",catalog,runtime)
    task = next(task for task in plan.tasks if task.map)
    with pytest.raises(ValueError,match="composition.expansion_resolution_required"):
        expand_map_item(plan,task,"0",True,runtime)


def test_selection_dependency_cannot_be_removed_from_portable_map(catalog):
    runtime = CapabilityRuntimeCatalog(catalog)
    plan = prepare_invocation("dynamic.map",catalog,runtime)
    restored = ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
    task = next(task for task in restored.tasks if task.map)
    selector = task.map.body.selection["format"]
    altered = replace(task,dependencies=tuple(key for key in task.dependencies if key != selector.task))
    tasks = tuple(altered if item.task_id == task.task_id else item for item in plan.tasks)
    changed = replace(plan,tasks=tasks)
    changed = replace(changed,plan_id=plan_identity(changed.definition_id,changed.tasks,changed.outputs,
        changed.scopes,changed.policy,changed.root_kind,changed.selected_bindings))
    with pytest.raises(ValueError,match="composition.dependency_missing"):
        validate_plan(changed,runtime)


def test_direct_static_and_dynamic_method_profile_reference_evidence_matches(catalog):
    from stratbox.capabilities.catalog import CatalogContribution
    from stratbox.core.execution.session import ExecutionSettings
    from stratbox.sdk import StrategyBox
    static = ScenarioDefinition("dynamic.static",GraphBody((
        Call("interpret","dynamic.interpret",inputs={"item":True},selection={"format":"csv"}),
    ),{"value":OutputRef("interpret")}),outputs={"value":RESULT})
    snapshot = catalog.overlay(CatalogContribution(definitions=(static,)))
    with StrategyBox(capabilities=snapshot,settings=ExecutionSettings(max_workers=1,map_window=1)) as box:
        direct = box.invoke("dynamic.interpret",inputs={"item":True},selection={"format":"csv"},timeout=10)
        composed = box.invoke("dynamic.static",timeout=10)
        mapped = box.invoke("dynamic.map",timeout=10)
        try:
            assert direct.outcome == composed.outcome == mapped.outcome == "succeeded",(
                direct.diagnostics,composed.diagnostics,mapped.diagnostics)
            assert direct.output("value") == composed.output("value")
            assert mapped.output("value") == (direct.output("value"),)
            identities = dict(direct.output("value"))
            assert {"method","profile","reference:dynamic.reference"} <= identities.keys()
        finally:
            direct.close()
            composed.close()
            mapped.close()


def test_expansion_resolution_preserves_scientific_input_evidence(catalog):
    from collections.abc import Mapping
    from datetime import date
    from stratbox.capabilities.commands import OBSERVATIONS
    from stratbox.shared.data.assessment import ValueEvidence,CoverageAssessment
    from stratbox.shared.data.observations import ObservationBatch,Observation,SubjectRef,MetricRef,PeriodRef
    from stratbox.shared.data.source_context import SourceCoordinate,SourceUse,ValueContext
    from stratbox.shared.evidence import SourcePayload,UsedInputReceipt
    payload = SourcePayload(b"reported observation","text/plain","dynamic.source")
    receipt = UsedInputReceipt.for_payload(payload,"source")
    source = SourceUse(SourceCoordinate("dynamic.source",semantic_profile_edition="2026"),qualification="reported")
    evidence = ValueEvidence(frozenset({"reported"}),CoverageAssessment("dynamic.source",(),True,(),None))
    row = Observation(SubjectRef("fixture","A"),MetricRef("balance","RUB","stock"),
        PeriodRef("as_of",as_of=date(2026,1,1)),(),"fixture",10,"reported","A1")
    batch = ObservationBatch("dynamic.observations",1,"2026",(row,),(receipt,),(source,),evidence)
    prepared = prepare_input(batch,OBSERVATIONS.schema,receipts=(receipt,),
        qualifications=frozenset({"reported"}),source_context=ValueContext((source,)))
    parameter = prepare_input("nominal basis",DataContract("dynamic.basis"),receipts=(receipt,),
                              source_context=ValueContext((source,)))
    replacements = {
        "dynamic.capture":replace(catalog.definition("dynamic.capture"),inputs={"observations":OBSERVATIONS},
                                  parameters={"profile":{},"basis":None}),
        "dynamic.interpret":replace(catalog.definition("dynamic.interpret"),inputs={"item":ITEM,"observations":OBSERVATIONS},
                                    parameters={"profile":{},"basis":None}),
        "dynamic.item_scenario":replace(catalog.definition("dynamic.item_scenario"),
            inputs={"item":ITEM,"observations":OBSERVATIONS},parameters={"basis":None},body=GraphBody((
                Call("interpret","dynamic.interpret",inputs={"item":InputRef("item"),"observations":InputRef("observations")},
                     parameters={"basis":ParameterRef("basis")}),
            ),{"value":OutputRef("interpret")})),
        "dynamic.map":replace(catalog.definition("dynamic.map"),inputs={"observations":OBSERVATIONS},parameters={"basis":None},body=GraphBody((
            Call("format","dynamic.format_operation"),
            MapCall("items","dynamic.item_scenario",(True,),inputs={"observations":InputRef("observations")},
                    parameters={"basis":ParameterRef("basis")},selection={"format":OutputRef("format")}),
            CollectCall("collected",(OutputRef("items"),),PortContract(DataContract("dynamic.results"),tuple,collection=True),RESULT),
        ),{"value":OutputRef("collected")})),
    }
    method = replace(catalog.method("dynamic.csv_method"),body=GraphBody((
        Call("capture","dynamic.capture",inputs={"observations":InputRef("observations")},
             parameters={"profile":ParameterRef("profile"),"basis":ParameterRef("basis")}),
    ),{"value":OutputRef("capture")}))
    snapshot = replace(catalog,definitions=tuple(replacements.get(item.capability_id,item) for item in catalog.definitions),methods=(method,))
    runtime = CapabilityRuntimeCatalog(snapshot)
    plan = prepare_invocation("dynamic.map",snapshot,runtime,inputs={"observations":prepared},parameters={"basis":parameter})
    task = next(task for task in plan.tasks if task.map)
    selector = task.map.body.selection["format"]
    def resolve(value):
        if value == selector:
            return prepare_input("csv",FORMAT.schema)
        if isinstance(value,Mapping):
            return {key:resolve(item) for key,item in value.items()}
        return value
    expanded = expand_map_item(plan,task,"0",True,runtime,resolve_value=resolve)
    leaf = next(task for task in expanded.tasks if task.operation_id == "dynamic.capture")
    admitted = leaf.inputs["observations"]
    assert admitted is prepared
    assert admitted.source_context == ValueContext((source,))
    assert admitted.used_inputs == (receipt,)
    assert admitted.value.evidence is evidence
    assert admitted.value.source_uses == (source,)
    assert leaf.parameters["basis"] is parameter
    assert leaf.parameters["basis"].source_context == ValueContext((source,))


def test_nested_portable_maps_preserve_selected_identity_basis(catalog):
    from stratbox.capabilities.catalog import CatalogContribution
    from stratbox.core.execution.session import ExecutionSettings
    from stratbox.sdk import StrategyBox
    items = PortContract(DataContract("dynamic.items"),tuple)
    results = PortContract(DataContract("dynamic.results"),tuple,collection=True)
    nested_results = PortContract(DataContract("dynamic.nested_results"),tuple,collection=True)
    inner = ScenarioDefinition("dynamic.inner",GraphBody((
        Call("format","dynamic.format_operation"),
        MapCall("items","dynamic.item_scenario",InputRef("item"),window=1,
                selection={"format":OutputRef("format")}),
        CollectCall("collected",(OutputRef("items"),),results,RESULT),
    ),{"value":OutputRef("collected")}),inputs={"item":items},outputs={"value":results})
    outer = ScenarioDefinition("dynamic.outer",GraphBody((
        MapCall("groups",inner.capability_id,((True,False),(False,)),window=1),
        CollectCall("collected",(OutputRef("groups"),),nested_results,results),
    ),{"value":OutputRef("collected")}),outputs={"value":nested_results})
    snapshot = catalog.overlay(CatalogContribution(definitions=(inner,outer)))
    with StrategyBox(capabilities=snapshot,settings=ExecutionSettings(max_workers=1,map_window=1)) as box:
        direct = box.invoke("dynamic.interpret",inputs={"item":True},selection={"format":"csv"},timeout=10)
        plan = box.prepare(outer.capability_id)
        restored = ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
        result = box.submit(restored).result(10)
        try:
            assert result.outcome == "succeeded",result.diagnostics
            expected = direct.output("value")
            assert result.output("value") == ((expected,expected),(expected,))
        finally:
            result.close()
            direct.close()


def test_selector_port_is_readmitted_before_expansion(catalog):
    runtime = CapabilityRuntimeCatalog(catalog)
    plan = prepare_invocation("dynamic.map",catalog,runtime)
    task = next(task for task in plan.tasks if task.map)
    bad_selector = replace(task.map.body.selection["format"],port="missing")
    changed_task = replace(task,map=replace(task.map,body=replace(task.map.body,selection={"format":bad_selector})))
    changed = replace(plan,tasks=tuple(changed_task if item.task_id == task.task_id else item for item in plan.tasks))
    changed = replace(changed,plan_id=plan_identity(changed.definition_id,changed.tasks,changed.outputs,
        changed.scopes,changed.policy,changed.root_kind,changed.selected_bindings))
    with pytest.raises(ValueError,match="composition.output_unknown"):
        validate_plan(changed,runtime)
