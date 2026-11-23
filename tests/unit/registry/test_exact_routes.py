"""Exact graphs explain declaration compatibility without acquiring materials."""
from dataclasses import dataclass

import pytest

from stratbox.core.execution import OperationDefinition
from stratbox.core.registry.catalog import OperationCatalog, OperationRef
from stratbox.core.registry.routes import connections, explain_route, stage_transitions
from stratbox.shared.data.operations import (
    InputPort, OperationSemantics, OutputPort, ProcessingFunction, ProcessingStage, RequestField,
)
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.routes import AvailableArtifact


@dataclass(frozen=True)
class One:
    value: str


@dataclass(frozen=True)
class Many:
    values: tuple[str, ...]


@dataclass(frozen=True)
class Pair:
    left: str
    right: str


RAW = DataContract("routes.raw")
EXTRACT = DataContract("routes.extract")
VIEW = DataContract("routes.view")
OTHER = DataContract("routes.other")


def definition(identity, inputs, output, *, request=One, function=ProcessingFunction.PROCESS,
               stages=(ProcessingStage.EXTRACT,), qualifications=frozenset(), effects=frozenset()):
    return OperationDefinition(identity, identity, request, str, possible_effects=effects,
        processing=OperationSemantics(stages, inputs=inputs,
            outputs=(OutputPort("result", output, qualifications=qualifications),),
            summary="Explain a typed fixture operation.", function=function),
        request_fields=tuple(RequestField(port.path, "input") for port in inputs))


def catalog(*definitions):
    # The handler is deliberately unavailable: graph inspection must stay lazy.
    return OperationCatalog(tuple(OperationRef(item.operation_id, "unavailable.handler:never", definition=item)
                                  for item in definitions))


def test_contract_edition_mismatch_is_explicit_and_stage_names_do_not_create_edges():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    target = definition("routes.consume", (InputPort("data", DataContract(EXTRACT.schema_id, 2), "value"),), VIEW)
    selected = catalog(source, target)
    assert connections(selected, producer=source.operation_id, consumer=target.operation_id).total == 0
    page = connections(selected, producer=source.operation_id, consumer=target.operation_id, include_incompatible=True)
    assert page.total == 1
    assert page.entries[0].state == "incompatible"
    assert page.entries[0].reasons == ("processing.schema_mismatch",)


def test_collection_and_extra_inputs_are_conditions_instead_of_false_direct_admission():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    target = definition("routes.integrate", (InputPort("data", EXTRACT, "values"),), VIEW, request=Many)
    pair = definition("routes.pair", (InputPort("left", EXTRACT, "left"), InputPort("right", OTHER, "right")), VIEW, request=Pair)
    selected = catalog(source, target, pair)
    item = connections(selected, producer=source.operation_id, consumer=target.operation_id).entries[0]
    assert item.kind == "collection"
    assert item.state == "conditional"
    assert "processing.collection_assembly_required" in item.reasons
    item = connections(selected, producer=source.operation_id, consumer=pair.operation_id).entries[0]
    assert item.additional_inputs == ("right",)


def test_collection_assembly_is_preserved_in_plans_and_effect_connections():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    save = definition("routes.save_many", (InputPort("data", EXTRACT, "values"),), VIEW,
        request=Many, effects=frozenset({"storage.write"}))
    selected = catalog(source, save)
    connection = connections(selected, producer=source.operation_id, consumer=save.operation_id).entries[0]
    assert connection.kind == "effect"
    required = {"processing.collection_cardinality_requires_admission", "processing.collection_assembly_required"}
    assert required <= set(connection.reasons)
    planned = explain_route(selected, save.operation_id, available=(RAW,))
    assert required <= set(planned.plans[0].conditions)
    collected = explain_route(catalog(save), save.operation_id,
        available=(AvailableArtifact(EXTRACT, collection=True),))
    assert "processing.collection_assembly_required" not in collected.plans[0].conditions
    assert "processing.collection_cardinality_requires_admission" in collected.plans[0].conditions


def test_replay_and_effect_connections_have_distinct_meaning():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    replay = definition("routes.replay", (InputPort("data", EXTRACT, "value"),), VIEW,
        stages=(), function=ProcessingFunction.REPLAY)
    effect = definition("routes.save", (InputPort("data", EXTRACT, "value"),), VIEW,
        effects=frozenset({"storage.write"}))
    selected = catalog(source, replay, effect)
    assert {item.kind for item in connections(selected, producer=source.operation_id).entries} == {"replay", "effect"}


def test_paging_is_stable_bounded_and_derived_stage_pairs_require_real_ports():
    from types import SimpleNamespace
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    target = definition("routes.view", (InputPort("data", EXTRACT, "value"),), VIEW,
        stages=(ProcessingStage.VIEW,))
    mismatch = definition("routes.other", (InputPort("other", OTHER, "value"),), RAW,
        stages=(ProcessingStage.ACQUIRE,))
    selected = catalog(source, target, mismatch)
    page = connections(selected, limit=1)
    assert len(page.entries) == 1
    assert page.next_offset is not None
    route = SimpleNamespace(operations=tuple(SimpleNamespace(operation_id=item.operation_id, formats=(), state="supported")
                                             for item in (source, target, mismatch)))
    pairs = stage_transitions(selected, route)
    assert (ProcessingStage.EXTRACT, ProcessingStage.VIEW) in pairs
    assert (ProcessingStage.EXTRACT, ProcessingStage.ACQUIRE) not in pairs
    with pytest.raises(ValueError, match="invalid_page"):
        connections(selected, limit=501)


def test_plan_requires_all_fanin_roles_and_never_promotes_claims_to_runtime_readiness():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    goal = definition("routes.pair", (InputPort("left", EXTRACT, "left"), InputPort("right", OTHER, "right")), VIEW, request=Pair)
    selected = catalog(source, goal)
    blocked = explain_route(selected, goal.operation_id, available=(RAW,))
    assert blocked.state == "unreachable"
    assert blocked.missing_inputs == ("routes.pair:right",)
    plan = explain_route(selected, goal.operation_id, available=(RAW, AvailableArtifact(OTHER, reference="fixture")))
    assert plan.state == "conditional"
    assert not plan.grants_authority
    assert plan.assessment_scope == "declaration_planning"
    assert tuple(step.operation_id for step in plan.plans[0].steps) == ("routes.extract", "routes.pair")
    assert "material.availability_requires_admission" in plan.plans[0].conditions


def test_plan_handles_already_available_goal_and_search_budget_without_execution():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    target = definition("routes.view", (InputPort("data", EXTRACT, "value"),), VIEW)
    selected = catalog(source, target)
    retained = explain_route(selected, VIEW, available=(VIEW,))
    assert retained.plans[0].steps == ()
    bounded = explain_route(selected, target.operation_id, available=(RAW,), max_nodes=1)
    assert bounded.truncated
    assert "planning.search_budget_exhausted" in bounded.reasons
    assert bounded.examined == 1


def test_depth_budget_counts_parallel_branches_by_depth_instead_of_total_steps():
    left = definition("routes.a_left", (InputPort("raw", RAW, "value"),), EXTRACT)
    right = definition("routes.b_right", (InputPort("raw", RAW, "value"),), OTHER)
    goal = definition("routes.c_pair", (InputPort("left", EXTRACT, "left"),
        InputPort("right", OTHER, "right")), VIEW, request=Pair)
    selected = catalog(left, right, goal)
    explanation = explain_route(selected, goal.operation_id, available=(RAW,), max_depth=2)
    assert tuple(step.operation_id for step in explanation.plans[0].steps) == (
        "routes.a_left", "routes.b_right", "routes.c_pair")
    assert not explanation.truncated
    deeper = definition("routes.d_deeper", (InputPort("view", VIEW, "value"),), DataContract("routes.final"))
    bounded = explain_route(catalog(left, right, goal, deeper), deeper.operation_id,
        available=(RAW,), max_depth=2)
    assert bounded.truncated
    assert bounded.state == "bounded"
    assert bounded.reasons == ("planning.search_budget_exhausted",)


def test_qualifications_and_effect_grants_remain_explicit_in_plan():
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    save = definition("routes.save", (InputPort("data", EXTRACT, "value", qualifications=frozenset({"reviewed"})),), VIEW,
        effects=frozenset({"storage.write"}))
    plan = explain_route(catalog(source, save), save.operation_id, available=(RAW,))
    assert "processing.qualification_missing" in plan.plans[0].conditions
    assert "effect.authorization_required:storage.write" in plan.plans[0].conditions


def test_planning_uses_metadata_without_typed_link_or_handler_resolution(monkeypatch):
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    target = definition("routes.view", (InputPort("data", EXTRACT, "value"),), VIEW)
    selected = catalog(source, target)
    def forbidden(*args, **kwargs):
        raise AssertionError("Planning cannot resolve executable or typed links")
    monkeypatch.setattr(OperationCatalog, "get", forbidden)
    monkeypatch.setattr(OperationCatalog, "resolve", forbidden)
    assert connections(selected, producer=source.operation_id).total == 1
    assert explain_route(selected, target.operation_id, available=(RAW,)).plans


def test_same_operation_can_have_a_compatible_exact_port_handoff():
    operation = definition("routes.refine", (InputPort("data", EXTRACT, "value"),), EXTRACT)
    page = connections(catalog(operation), producer=operation.operation_id, consumer=operation.operation_id)
    assert page.total == 1
    assert page.entries[0].state == "compatible"


def test_source_qualification_reasons_survive_graph_and_planning_selection(monkeypatch):
    from types import SimpleNamespace
    from stratbox.core.registry.source_catalog import SourceOperation
    source = definition("routes.extract", (InputPort("raw", RAW, "value"),), EXTRACT)
    target = definition("routes.view", (InputPort("data", EXTRACT, "value"),), VIEW)
    selected = catalog(source, target)
    bindings = (SourceOperation(source.operation_id, "conditional", "A reviewed profile is required."),
                SourceOperation(target.operation_id))
    assessments = tuple(SimpleNamespace(binding=binding, state=binding.state,
        reasons=("source.profile_required",) if binding.state == "conditional" else ()) for binding in bindings)
    selection = SimpleNamespace(bindings=bindings, assessments=assessments)
    monkeypatch.setattr(OperationCatalog, "source_catalog", lambda _: SimpleNamespace(selection=lambda *args, **kwargs: selection))
    page = connections(selected, source_id="example", producer=source.operation_id, consumer=target.operation_id)
    assert "source.profile_required" in page.entries[0].reasons
    explanation = explain_route(selected, target.operation_id, source_id="example", available=(RAW,))
    assert "source.profile_required" in explanation.plans[0].conditions
    selection.bindings = bindings[:1]
    selection.assessments = (assessments[0], SimpleNamespace(binding=bindings[1], state="inapplicable",
        reasons=("source.format_unavailable",)))
    explanation = explain_route(selected, target.operation_id, source_id="example", available=(RAW,))
    assert explanation.state == "unreachable"
    assert explanation.reasons == ("source.format_unavailable",)
