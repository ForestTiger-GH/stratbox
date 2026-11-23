"""Exact port graphs and bounded, non-executing dependency explanations.

The graph is derived from canonical ports and source applicability. Neither a
stage label nor a proposed plan grants material availability or effect authority.
"""
from __future__ import annotations

from dataclasses import MISSING, dataclass, fields, is_dataclass
from typing import get_args, get_origin, get_type_hints

from stratbox.shared.data.operations import OperationKey, ProcessingFunction, ProcessingStage, assess_input
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.routes import (
    AvailableArtifact, ConnectionPage, ExactConnection, PlannedStep, RouteExplanation, RoutePlan,
)


class _Selected(dict):
    def __init__(self, values, *, conditions=None, rejected=None):
        super().__init__(values)
        self.conditions = conditions or {}
        self.rejected = rejected or {}


def _selection(catalog, source_id, format, group_id, edition):
    if source_id is None:
        if any(value is not None for value in (format, group_id, edition)):
            raise ValueError("planning.source_required")
        return _Selected({ref.operation_id: None for ref in catalog.list_refs()})
    selection = catalog.source_catalog().selection(source_id, format=format,
        group_id=group_id, edition=edition)
    return _Selected({binding.operation_id: binding for binding in selection.bindings},
        conditions={item.binding.operation_id: item.reasons for item in selection.assessments
                    if item.state != "inapplicable"},
        rejected={item.binding.operation_id: item.reasons for item in selection.assessments
                  if item.state == "inapplicable"})


def _required_parameters(definition, binding=None):
    semantics = definition.processing
    if semantics is None:
        return ()
    supplied = {name for name, _ in getattr(binding, "parameters", ())}
    identity = getattr(binding, "identity_parameter", None)
    if identity is not None:
        supplied.add(identity)
    if not is_dataclass(definition.request_type):
        return tuple(name for name in getattr(semantics, "required_parameters", semantics.parameters) if name not in supplied)
    declared = {field.name: field for field in fields(definition.request_type)}
    return tuple(name for name in semantics.parameters if name not in supplied and (
        name not in declared or declared[name].default is MISSING and declared[name].default_factory is MISSING))


def _path_type(kind, path):
    for name in path.split(".") if path else ():
        try:
            kind = get_type_hints(kind).get(name)
        except (TypeError, NameError):
            return None
        if kind is None:
            return None
    return kind


def _collection(kind):
    if kind in (tuple, list):
        return True
    origin = get_origin(kind)
    if origin in (tuple, list):
        return True
    return any(_collection(item) for item in get_args(kind))


def _kind(producer, output, consumer, input):
    semantics = consumer.processing
    if semantics.function is ProcessingFunction.REPLAY:
        return "replay"
    if consumer.possible_effects:
        return "effect"
    if semantics.composition:
        return "composite"
    if getattr(input, "collection", False) or _collection(_path_type(consumer.request_type, input.path)):
        return "collection"
    roles = {port.contract.role.value for port in semantics.outputs if port.contract.role is not None}
    if "integrated" in roles and output.contract.role is not None and output.contract.role.value != "integrated":
        return "conversion"
    if ProcessingStage.VIEW in semantics.stages:
        return "projection"
    return "direct"


def _connections(catalog, selected, *, source_id=None, format=None, group_id=None, edition=None,
                 producer=None, output=None, consumer=None, input=None, include_incompatible=False):
    metadata = getattr(catalog, "metadata", catalog.get)
    definitions = {identity: metadata(identity) for identity in sorted(selected)}
    if producer is not None and producer not in definitions:
        if producer in getattr(selected, "rejected", {}):
            raise ValueError((selected.rejected[producer] or ("source.operation_inapplicable",))[0])
        raise ValueError("planning.producer_unavailable")
    if consumer is not None and consumer not in definitions:
        if consumer in getattr(selected, "rejected", {}):
            raise ValueError((selected.rejected[consumer] or ("source.operation_inapplicable",))[0])
        raise ValueError("planning.consumer_unavailable")
    producers = [definitions[producer]] if producer is not None else definitions.values()
    consumers = [definitions[consumer]] if consumer is not None else definitions.values()
    for produced in producers:
        if produced.processing is None:
            continue
        outputs = tuple(port for port in produced.processing.outputs if output is None or port.name == output)
        if output is not None and producer is not None and not outputs:
            raise ValueError("processing.output_unavailable")
        for accepted in consumers:
            if accepted.processing is None:
                continue
            inputs = tuple(port for port in accepted.processing.inputs if input is None or port.name == input)
            if input is not None and consumer is not None and not inputs:
                raise ValueError("processing.input_unavailable")
            for from_port in outputs:
                for to_port in inputs:
                    contracts = (to_port.contract, *to_port.alternatives)
                    if from_port.contract not in contracts and not include_incompatible:
                        continue
                    incompatible, conditions = [], []
                    selection_conditions = getattr(selected, "conditions", {})
                    conditions.extend(selection_conditions.get(produced.operation_id, ()))
                    conditions.extend(selection_conditions.get(accepted.operation_id, ()))
                    if from_port.contract not in contracts:
                        incompatible.append("processing.schema_mismatch")
                    if not from_port.outcomes & to_port.outcomes:
                        incompatible.append("processing.outcome_not_accepted")
                    if not to_port.qualifications <= from_port.qualifications:
                        conditions.append("processing.qualification_missing")
                    if not to_port.coverage <= from_port.coverage:
                        conditions.append("processing.coverage_missing")
                    additional = tuple(port.name for port in accepted.processing.inputs if port.required and port.name != to_port.name)
                    parameters = _required_parameters(accepted, selected[accepted.operation_id])
                    if additional:
                        conditions.append("processing.additional_inputs_required")
                    if parameters:
                        conditions.append("processing.parameters_required")
                    kind = _kind(produced, from_port, accepted, to_port)
                    collection = getattr(to_port, "collection", False) or _collection(_path_type(accepted.request_type, to_port.path))
                    if collection:
                        conditions.append("processing.collection_cardinality_requires_admission")
                    if collection and not (getattr(from_port, "collection", False) or _collection(_path_type(produced.value_type, from_port.path))):
                        conditions.append("processing.collection_assembly_required")
                    binding = selected[accepted.operation_id]
                    if binding is not None and binding.state == "conditional":
                        conditions.append("source.operation_conditional")
                    if incompatible and not include_incompatible:
                        continue
                    yield ExactConnection(OperationKey(produced.operation_id), from_port.name,
                        OperationKey(accepted.operation_id), to_port.name, kind, from_port.contract,
                        contracts, "incompatible" if incompatible else "conditional" if conditions else "compatible",
                        tuple(dict.fromkeys(incompatible + conditions)), additional, parameters, source_id, group_id, edition,
                        format=format)


def connections(catalog, *, source_id=None, format=None, group_id=None, edition=None,
                producer=None, output=None, consumer=None, input=None,
                include_incompatible=False, offset=0, limit=100):
    """Page exact declared links; incompatible links require an explicit query."""
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("planning.invalid_page")
    if type(include_incompatible) is not bool:
        raise ValueError("planning.invalid_filter")
    selected = _selection(catalog, source_id, format, group_id, edition)
    edges = tuple(_connections(catalog, selected, source_id=source_id, format=format, group_id=group_id,
        edition=edition, producer=producer, output=output, consumer=consumer, input=input,
        include_incompatible=include_incompatible))
    page = edges[offset:offset + limit]
    following = offset + len(page)
    return ConnectionPage(page, offset, len(edges), following if following < len(edges) else None)


def stage_transitions(catalog, route, *, format=None, group_id=None, edition=None):
    """Project stage pairs from exact ports; stages themselves grant no handoff."""
    selected = {binding.operation_id: binding for binding in route.operations
        if not (format is not None and binding.formats and format not in binding.formats)}
    pairs = set()
    for edge in _connections(catalog, selected):
        metadata = getattr(catalog, "metadata", catalog.get)
        before = metadata(edge.producer.operation_id).processing
        after = metadata(edge.consumer.operation_id).processing
        pairs.update((left, right) for left in before.stages for right in after.stages if left != right)
    return tuple(sorted(pairs, key=lambda pair: (pair[0].value, pair[1].value)))


@dataclass(frozen=True)
class _Fact:
    contract: DataContract
    outcome: str
    qualifications: frozenset[str]
    coverage: frozenset[str]
    steps: tuple[PlannedStep, ...] = ()
    conditions: tuple[str, ...] = ()
    depth: int = 0
    collection: bool = False


def _artifact(value):
    if isinstance(value, DataContract):
        return AvailableArtifact(value)
    if isinstance(value, AvailableArtifact):
        return value
    if hasattr(value, "contract") and hasattr(value, "value"):
        return AvailableArtifact(value.contract, outcome=value.outcome,
            qualifications=value.qualifications, coverage=value.coverage,
            collection=isinstance(value.value, (tuple, list)))
    raise ValueError("planning.artifact_invalid")


def explain_route(catalog, goal, *, available=(), source_id=None, format=None,
                  group_id=None, edition=None, max_depth=8, max_nodes=1000, max_plans=5):
    """Forward-chain AND dependencies without invoking handlers or providers."""
    if not isinstance(goal, (str, DataContract)):
        raise ValueError("planning.goal_invalid")
    if any(type(value) is not int or not 1 <= value <= maximum for value, maximum in (
        (max_depth, 32), (max_nodes, 10000), (max_plans, 20))):
        raise ValueError("planning.invalid_budget")
    if not isinstance(available, (tuple, list)) or len(available) > 1000:
        raise ValueError("planning.artifacts_invalid")
    selected = _selection(catalog, source_id, format, group_id, edition)
    metadata = getattr(catalog, "metadata", catalog.get)
    definitions = {identity: metadata(identity) for identity in sorted(selected)}
    if isinstance(goal, str) and goal not in definitions:
        if goal in selected.rejected:
            return RouteExplanation(goal, (), (), selected.rejected[goal], 0, False, source_id,
                                    format=format, group_id=group_id, edition=edition)
        raise ValueError("planning.goal_unavailable")
    facts = []
    for item in available:
        artifact = _artifact(item)
        # Supplied artifact descriptions are claims. This API never reads a
        # provider and cannot promote them into execution-readiness proof.
        facts.append(_Fact(artifact.contract, artifact.outcome, artifact.qualifications,
            artifact.coverage, conditions=("material.availability_requires_admission",),
            collection=artifact.collection))
    completed, plans, examined, truncated = set(), [], 0, False
    depth_limited = set()
    missing = {}
    for _ in range(max_depth):
        changed = False
        for identity, definition in definitions.items():
            if identity in completed or definition.processing is None:
                continue
            if examined >= max_nodes:
                truncated = True
                break
            examined += 1
            semantics = definition.processing
            chosen, absent, conditions = [], [], []
            for port in semantics.inputs:
                matches = []
                for fact in facts:
                    assessment = assess_input(port, fact.contract, outcome=fact.outcome,
                        qualifications=fact.qualifications, coverage=fact.coverage)
                    if fact.contract in (port.contract, *port.alternatives) and fact.outcome in port.outcomes:
                        matches.append((fact, assessment))
                if not matches:
                    if port.required:
                        absent.append(port.name)
                    continue
                fact, assessment = min(matches, key=lambda item: (
                    len(item[0].conditions) + len(item[1].reasons), len(item[0].steps),
                    tuple(step.operation_id for step in item[0].steps)))
                chosen.append(fact)
                conditions.extend(fact.conditions)
                conditions.extend(assessment.reasons)
                if getattr(port, "collection", False) or _collection(_path_type(definition.request_type, port.path)):
                    conditions.append("processing.collection_cardinality_requires_admission")
                    if not fact.collection:
                        conditions.append("processing.collection_assembly_required")
            missing[identity] = tuple(absent)
            if absent:
                continue
            steps = {step.operation_id: step for fact in chosen for step in fact.steps}
            if identity in steps:
                continue
            depth = max((fact.depth for fact in chosen), default=0) + 1
            if depth > max_depth:
                depth_limited.add(identity)
                continue
            parameters = _required_parameters(definition, selected[identity])
            conditions.extend("parameter.required:" + name for name in parameters)
            conditions.extend("provider.required:" + role for role in sorted(definition.required_capabilities))
            conditions.extend("effect.authorization_required:" + effect for effect in sorted(definition.possible_effects))
            binding = selected[identity]
            conditions.extend(selected.conditions.get(identity, ()))
            if binding is not None and binding.state == "conditional":
                conditions.append("source.operation_conditional")
            from stratbox.core.registry.requirements import describe_source_requirements
            for requirement in describe_source_requirements(catalog, identity):
                if requirement["required"]:
                    conditions.append("source.role_requires_admission:" + requirement["input_name"])
            step = PlannedStep(identity, tuple(steps), tuple(port.name for port in semantics.inputs if port.required),
                tuple(sorted(set(conditions))), tuple(sorted(definition.possible_effects)))
            steps[identity] = step
            ordered = tuple(steps.values())
            conditions = tuple(sorted(set(conditions)))
            completed.add(identity)
            depth_limited.discard(identity)
            changed = True
            if goal == identity:
                plans.append(RoutePlan(ordered, conditions))
            for port in semantics.outputs:
                for outcome in sorted(port.outcomes):
                    collection = getattr(port, "collection", False) or _collection(_path_type(definition.value_type, port.path))
                    fact = _Fact(port.contract, outcome, port.qualifications, port.coverage,
                        ordered, conditions, depth, collection)
                    facts.append(fact)
                    if isinstance(goal, DataContract) and goal == fact.contract:
                        plans.append(RoutePlan(ordered, conditions))
        if truncated or not changed:
            break
    if isinstance(goal, DataContract):
        seeds = [fact for fact in facts if fact.contract == goal and not fact.steps]
        plans.extend(RoutePlan((), fact.conditions) for fact in seeds)
    plans.sort(key=lambda plan: (len(plan.conditions), len(plan.steps), tuple(step.operation_id for step in plan.steps)))
    unique = {}
    for plan in plans:
        unique.setdefault(tuple(step.operation_id for step in plan.steps), plan)
    if isinstance(goal, str):
        needed = tuple(goal + ":" + name for name in missing.get(goal, ()))
    else:
        needed = () if plans else (goal.schema_id,)
    truncated = truncated or bool(depth_limited)
    reasons = ("planning.search_budget_exhausted",) if truncated else () if plans else ("planning.no_declared_path",)
    return RouteExplanation(goal, tuple(unique.values())[:max_plans], needed, reasons, examined,
                            truncated, source_id, format=format, group_id=group_id, edition=edition)
