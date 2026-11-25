"""Deterministic expansion and admission of declared workflow graphs."""
from __future__ import annotations

from dataclasses import dataclass, fields, replace, is_dataclass
from graphlib import TopologicalSorter, CycleError
from typing import Mapping

from stratbox.capabilities.model.definitions import declaration_fingerprint
from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput, prepare_input, adapt_input
from stratbox.core.execution.methods import method_descriptor
from stratbox.core.execution.values import argument_identity
from stratbox.shared.data.operations import OutputPort, compatible_ports, assess_input
from .plan import ScopeOutputRef, task_conditions, ExpansionValueResolver
from .models import (
    CascadeDefinition, CollectStep, CompiledMap, CompiledTask, CompositionError,
    ExecutionPlan, InputRef, MapStep, OperationStep, PlanOutputRef, PlanScope,
    ScenarioDefinition, ScenarioStep,
)


def iter_references(value):
    """Visit symbolic output references, without traversing data payloads."""
    if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from iter_references(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from iter_references(item)


def replace_references(value, transform):
    if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
        return transform(value)
    if isinstance(value, Mapping):
        return {key: replace_references(item, transform) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(replace_references(item, transform) for item in value)
    if isinstance(value, list):
        return [replace_references(item, transform) for item in value]
    return value


@dataclass(frozen=True)
class _DeferredInput:
    name: str
    contract: object


def _inputs(value, supplied):
    if isinstance(value, InputRef):
        if value.name not in supplied:
            raise CompositionError("composition.input_required")
        return supplied[value.name]
    if isinstance(value, Mapping):
        return {k: _inputs(v, supplied) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(_inputs(v, supplied) for v in value)
    if isinstance(value, list):
        return [_inputs(v, supplied) for v in value]
    return value


def _deferred(value):
    if isinstance(value, _DeferredInput):
        return True
    if isinstance(value, Mapping):
        return any(_deferred(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return any(_deferred(v) for v in value)
    return False


def _source_parameters(catalog, source, definition, parameters):
    if source is None:
        return parameters
    binding = catalog.bind_source(source.series_id, format=source.format, group_id=source.group_id, edition=source.edition)
    selection = catalog.source_catalog().selection(source.series_id, format=source.format, group_id=source.group_id, edition=source.edition)
    choices = [entry for entry in selection.bindings if entry.operation_id == definition.operation_id]
    if len(choices) != 1:
        raise CompositionError("source.operation_unbound")
    chosen = choices[0]
    values = dict(parameters)
    for key, value in chosen.parameters:
        if key in values and values[key] != value:
            raise CompositionError("source.parameter_conflict")
        values[key] = value
    if chosen.identity_parameter:
        from stratbox.core.execution.handoff import request_type_hints
        from typing import get_origin
        parameter = chosen.identity_parameter
        annotation = request_type_hints(definition.request_type).get(parameter)
        value = (source.series_id,) if get_origin(annotation) is tuple else source.series_id
        if parameter in values and values[parameter] != value:
            raise CompositionError("source.parameter_conflict")
        values[parameter] = value
    return values


def _require_atomic(definition):
    if definition.processing is None or not definition.processing.composition:
        return
    raise CompositionError("composition.scenario_required")


def _authoring_references(value):
    if isinstance(value, InputRef):
        yield value
    elif isinstance(value, (PlanOutputRef,ScopeOutputRef)):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _authoring_references(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _authoring_references(item)


def _prune_definition(definition, selected):
    """Select symbolic closure before resolving methods or requiring inputs."""
    if selected is None:
        return definition
    selected = (selected,) if isinstance(selected, str) else tuple(selected)
    if set(selected) - set(definition.outputs):
        raise CompositionError("composition.output_unknown")
    outputs = {name: definition.outputs[name] for name in selected}
    steps = {step.step_id: step for step in definition.steps}
    roots = {ref.task for ref in iter_references(outputs)}
    roots.update(definition.required_checks)
    roots.update(definition.required_effects)
    # Child obligations remain roots even when no child data output is selected.
    roots.update(step.step_id for step in definition.steps if isinstance(step, ScenarioStep)
                 and (step.scenario.required_checks or step.scenario.required_effects))
    keep = set()
    pending = list(roots)
    while pending:
        key = pending.pop()
        if key in keep:
            continue
        if key not in steps:
            raise CompositionError("composition.task_unknown")
        keep.add(key)
        step = steps[key]
        pending.extend(step.depends_on)
        values = (getattr(step, "inputs", {}), getattr(step, "parameters", {}),
                  getattr(step, "items", ()), getattr(getattr(step, "collect", None), "inputs", ()))
        pending.extend(ref.task for ref in iter_references(values))
        condition = getattr(step, "condition", None)
        if condition is not None:
            pending.append(condition.task)
    kept = []
    used_inputs = {ref.name for ref in _authoring_references(outputs) if isinstance(ref, InputRef)}
    for step in definition.steps:
        if step.step_id not in keep:
            continue
        if isinstance(step, ScenarioStep):
            requested = {ref.port for value in (outputs, *[getattr(other, "inputs", {}) for other in definition.steps if other.step_id in keep],
                                                     *[getattr(other, "parameters", {}) for other in definition.steps if other.step_id in keep])
                         for ref in iter_references(value) if ref.task == step.step_id}
            child = _prune_definition(step.scenario, requested if requested else None)
            step = replace(step, scenario=child, inputs={key:value for key,value in step.inputs.items() if key in child.inputs})
        for value in (getattr(step, "inputs", {}), getattr(step, "parameters", {}), getattr(step, "items", ())):
            used_inputs.update(ref.name for ref in _authoring_references(value) if isinstance(ref, InputRef))
        kept.append(step)
    return replace(definition, steps=tuple(kept), outputs=outputs,
                   inputs={name: contract for name, contract in definition.inputs.items() if name in used_inputs})


def plan_identity(definition_id, tasks, outputs, scopes, policy="continue", root_kind="scenario", selected_bindings=None):
    from stratbox.capabilities.model.definitions import declaration_tree
    encoded_scopes = tuple(replace(scope, output_contracts={name: declaration_tree(port)
        for name, port in scope.output_contracts.items()},
        acceptance=declaration_tree(scope.acceptance)) for scope in scopes)
    return argument_identity((definition_id, tuple(tasks), outputs, encoded_scopes, policy,
                              root_kind, selected_bindings or {})).sha256


class Compiler:
    def __init__(self, catalog):
        self.catalog = catalog

    def compile(self, definition, **options):
        return compile_workflow(definition, self.catalog, **options)


def compile_workflow(definition, catalog, *, inputs=None, parameters=None, outputs=None, prefix=None, _defer=False):
    """Compile one scenario/cascade, optionally selecting an output closure.

    InputRef names include both typed data inputs and ordinary parameter
    placeholders. Explicit local data is never replaced by network acquisition.
    Nested scenarios flatten into scopes; maps retain their bounded template.
    """
    root_kind = "cascade" if isinstance(definition, CascadeDefinition) else "scenario"
    if isinstance(definition, CascadeDefinition):
        definition = definition.as_scenario()
    if not isinstance(definition, ScenarioDefinition):
        raise CompositionError("composition.definition_required")
    original_inputs = set(definition.inputs)
    definition = _prune_definition(definition, outputs)
    supplied = {name: value for name, value in (inputs or {}).items() if name in definition.inputs or name not in original_inputs}
    if set(supplied) & set(parameters or {}):
        raise CompositionError("composition.parameter_conflict")
    supplied.update({name:value for name,value in (parameters or {}).items() if name in definition.inputs or name not in original_inputs})
    tasks = []
    scopes = []
    aliases = {}
    scenario_members = {}
    definitions = {}
    fingerprints = {}
    map_ports = {}

    def qualify(ref, scope):
        return replace(ref, task=scope + "/" + ref.task)

    def resolve(value, arguments, scope):
        # Supplied values already belong to their caller's scope.
        if isinstance(value, InputRef):
            if value.name not in arguments:
                raise CompositionError("composition.input_required")
            return arguments[value.name]
        if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
            return qualify(value, scope)
        if isinstance(value, Mapping):
            return {k: resolve(v, arguments, scope) for k, v in value.items()}
        if isinstance(value, tuple):
            return tuple(resolve(v, arguments, scope) for v in value)
        if isinstance(value, list):
            return [resolve(v, arguments, scope) for v in value]
        return value

    def flatten(scenario, scope, arguments, parent=None, extra_dependencies=(), required=True):
        if set(arguments) - set(scenario.inputs):
            raise CompositionError("composition.input_unknown")
        if set(scenario.inputs) - set(arguments):
            raise CompositionError("composition.input_required")
        arguments = dict(arguments)
        for name, contract in scenario.inputs.items():
            value = arguments[name]
            if contract is not None and not isinstance(value, (PlanOutputRef, PreparedInput, ProjectedOutput, _DeferredInput)):
                arguments[name] = prepare_input(value, contract)
            elif contract is not None and isinstance(value, (PreparedInput, ProjectedOutput)) and value.contract != contract:
                raise CompositionError("composition.input_contract_mismatch")
        scope_position = len(scopes)
        scopes.append(PlanScope(scope, scenario.scenario_id, parent, scenario.expenditure,
                                kind=root_kind if parent is None else "scenario", required=required,
                                required_checks=tuple(scope + "/" + key for key in scenario.required_checks),
                                required_effects=tuple(scope + "/" + key for key in scenario.required_effects)))
        start = len(tasks)
        for step in scenario.steps:
            task_id = scope + "/" + step.step_id
            dependencies = tuple(dict.fromkeys((*extra_dependencies, *(scope + "/" + dep for dep in step.depends_on))))
            if isinstance(step, ScenarioStep):
                child_inputs = resolve(step.inputs, arguments, scope)
                child_outputs = flatten(step.scenario, task_id, child_inputs, scope, dependencies, required and step.required)
                for name, value in child_outputs.items():
                    aliases[(task_id, name)] = value
                continue
            if isinstance(step, OperationStep):
                operation = definitions.setdefault(step.operation_id, catalog.get(step.operation_id))
                _require_atomic(operation)
                semantics = operation.processing
                if semantics is None:
                    raise CompositionError("composition.processing_required")
                bound_inputs = resolve(step.inputs, arguments, scope)
                params = resolve(step.parameters, arguments, scope)
                params = _source_parameters(catalog, step.source, operation, params)
                if set(params) - set(semantics.parameters):
                    raise CompositionError("handoff.parameter_unknown")
                if set(semantics.required_parameters) - set(params):
                    raise CompositionError("handoff.parameter_required")
                if step.operation_id not in fingerprints:
                    work = None if operation.method_refs else catalog.resolve(step.operation_id)[1]
                    fingerprints[step.operation_id] = method_descriptor(operation, work=work).identity.sha256
                condition = replace(step.condition, task=scope + "/" + step.condition.task) if step.condition else None
                tasks.append(CompiledTask(task_id, step.operation_id, bound_inputs, params, dependencies,
                    scope, required and step.required, condition, step.source, resources=step.resources,
                    retry=step.retry, method_id=operation.method_id, method_fingerprint=fingerprints[step.operation_id], share_key=step.share_key))
            elif isinstance(step, MapStep):
                child_arguments = resolve(step.inputs, arguments, scope)
                if step.item_input in child_arguments:
                    raise CompositionError("composition.map_item_conflict")
                placeholders = {name: _DeferredInput(name, contract) for name, contract in step.body.inputs.items()}
                if set(child_arguments) != set(step.body.inputs) - {step.item_input}:
                    raise CompositionError("composition.map_inputs_incomplete")
                probe = compile_workflow(step.body, catalog, inputs=placeholders, _defer=True)
                map_ports[task_id] = _plan_ports(probe, catalog)
                mapped = CompiledMap(step.body, resolve(step.items, arguments, scope), step.item_input,
                    step.key_field, step.window, child_arguments, step.allow_partial, probe.plan_id)
                tasks.append(CompiledTask(task_id, None, {}, {}, dependencies, scope, required and step.required, map=mapped))
            elif isinstance(step, CollectStep):
                spec = replace(step.collect, inputs=tuple(resolve(v, arguments, scope) for v in step.collect.inputs))
                tasks.append(CompiledTask(task_id, None, {}, {}, dependencies, scope, required and step.required, collect=spec))
        scenario_members[scope] = tuple(task.task_id for task in tasks[start:])
        scope_outputs = {name: resolve(value, arguments, scope) for name, value in scenario.outputs.items()}
        scopes[scope_position] = replace(scopes[scope_position], outputs=scope_outputs)
        return scope_outputs

    scope = prefix or definition.scenario_id
    if not isinstance(scope, str) or not scope or any(part in {"", ".", ".."} for part in scope.split("/")):
        raise CompositionError("composition.invalid_scope")
    declared_outputs = flatten(definition, scope, supplied)

    def unalias(ref, trail=()):
        key = (ref.task, ref.port)
        if key not in aliases:
            return ref
        if key in trail:
            raise CompositionError("composition.cycle")
        value = aliases[key]
        if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
            value = unalias(value, (*trail, key))
            if ref.item is not None:
                if not isinstance(value, (PlanOutputRef,ScopeOutputRef)) or value.item is not None:
                    raise CompositionError("composition.invalid_item")
                value = replace(value, item=ref.item)
        elif ref.item is not None:
            raise CompositionError("composition.invalid_item")
        return value

    final = []
    for task in tasks:
        task_inputs = replace_references(task.inputs, unalias)
        task_params = replace_references(task.parameters, unalias)
        mapped = task.map
        collected = task.collect
        if mapped is not None:
            mapped = replace(mapped, items=replace_references(mapped.items, unalias), inputs=replace_references(mapped.inputs, unalias))
        if collected is not None:
            collected = replace(collected, inputs=tuple(unalias(ref) for ref in collected.inputs))
        dependencies = []
        for dependency in task.dependencies:
            dependencies.extend(scenario_members.get(dependency, (dependency,)))
        refs = (*iter_references(task_inputs), *iter_references(task_params),
                *iter_references(mapped.items if mapped else ()), *iter_references(mapped.inputs if mapped else ()),
                *(collected.inputs if collected else ()))
        dependencies.extend(ref.task for ref in refs)
        if task.condition is not None:
            dependencies.append(task.condition.task)
        final.append(replace(task, inputs=task_inputs, parameters=task_params, map=mapped, collect=collected,
                             dependencies=tuple(dict.fromkeys(dependencies))))
    tasks = final
    declared_outputs = replace_references(declared_outputs, unalias)
    index = {task.task_id: task for task in tasks}
    if len(index) != len(tasks):
        raise CompositionError("composition.duplicate_task")
    for task in tasks:
        if set(task.dependencies) - set(index):
            raise CompositionError("composition.task_unknown")
    try:
        order = tuple(TopologicalSorter({task.task_id: task.dependencies for task in tasks}).static_order())
    except CycleError:
        raise CompositionError("composition.cycle") from None
    tasks = [index[key] for key in order]

    def port(ref):
        if ref.task not in index:
            raise CompositionError("composition.task_unknown")
        producer = index[ref.task]
        if producer.operation_id:
            ports = definitions[producer.operation_id].processing.outputs
        elif producer.collect:
            ports = (OutputPort("value", producer.collect.contract, outcomes=frozenset({"succeeded", "partial"}) if producer.collect.allow_partial else frozenset({"succeeded"})),)
        else:
            ports = map_ports[ref.task]
        found = next((item for item in ports if item.name == ref.port), None)
        if found is None:
            raise CompositionError("composition.output_unknown")
        if ref.item is not None and producer.map is None:
            raise CompositionError("composition.item_requires_map")
        return found

    for task in tasks:
        if task.operation_id:
            operation = definitions[task.operation_id]
            semantics = operation.processing
            ports = {item.name: item for item in semantics.inputs}
            if set(task.inputs) - set(ports):
                raise CompositionError("handoff.input_unknown")
            if any(item.required and item.name not in task.inputs for item in ports.values()):
                raise CompositionError("handoff.input_required")
            for name, value in task.inputs.items():
                target = ports[name]
                if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
                    output_port = port(value)
                    if index[value.task].map is not None and value.item is None:
                        raise CompositionError("composition.map_collect_required")
                    if not compatible_ports(output_port, target):
                        raise CompositionError("processing.schema_mismatch")
                elif isinstance(value, _DeferredInput):
                    if value.contract is not None and value.contract not in (target.contract, *target.alternatives):
                        raise CompositionError("processing.schema_mismatch")
                else:
                    if tuple(iter_references(value)):
                        raise CompositionError("composition.collection_contract_required")
                    prepared = adapt_input(value)
                    assessment = assess_input(target, prepared.contract, outcome=prepared.outcome,
                        qualifications=prepared.qualifications, coverage=prepared.coverage)
                    if not assessment.compatible:
                        raise CompositionError(assessment.reasons[0])
            if not tuple(iter_references(task.inputs)) and not tuple(iter_references(task.parameters)) and not _deferred((task.inputs, task.parameters)):
                if task.source:
                    catalog.bind_source(task.source.series_id, format=task.source.format, group_id=task.source.group_id, edition=task.source.edition).bind(task.operation_id, inputs=task.inputs, parameters=task.parameters)
                else:
                    catalog.bind(task.operation_id, inputs=task.inputs, parameters=task.parameters)
            for reference in iter_references(task.parameters):
                port(reference)
            _validate_parameters(task, index, catalog)
        if task.collect:
            for value in task.collect.inputs:
                contract = port(value).contract if isinstance(value,PlanOutputRef) else adapt_input(value).contract
                if contract != task.collect.element_contract:
                    raise CompositionError("processing.schema_mismatch")
        if task.condition:
            if task.condition.task not in index:
                raise CompositionError("composition.task_unknown")
            if task.condition.port:
                port(PlanOutputRef(task.condition.task, task.condition.port))
                _validate_condition(task.condition, index, catalog)
        if task.map:
            for reference in (*iter_references(task.map.items), *iter_references(task.map.inputs)):
                port(reference)
    for reference in iter_references(declared_outputs):
        port(reference)

    # Explicit sharing is restricted to effect-free calls. The key expresses
    # caller intent; exact scope, inputs, method, source, condition and policy
    # still have to agree. Shared prerequisites across independently cancellable
    # scopes are explicit parent nodes. Network observations share through access.
    shared = {}
    replacements = {}
    physical = []
    for task in tasks:
        if task.share_key is None:
            physical.append(task)
            continue
        if task.operation_id is None or definitions[task.operation_id].possible_effects:
            raise CompositionError("composition.effect_sharing_forbidden")
        identity = argument_identity((task.scope_id, task.operation_id, task.inputs, task.parameters, task.source,
            task.method_fingerprint, task.condition, task.dependencies, task.resources, task.retry)).sha256
        key = (task.share_key, identity)
        if key in shared:
            owner = shared[key]
            replacements[task.task_id] = owner
            for position, previous in enumerate(physical):
                if previous.task_id == owner:
                    physical[position] = replace(previous, aliases=(*previous.aliases, task.task_id), required=previous.required or task.required)
                    break
        else:
            shared[key] = task.task_id
            physical.append(task)
    if replacements:
        def shared_ref(ref):
            return replace(ref, task=replacements.get(ref.task, ref.task))
        tasks = []
        for task in physical:
            mapped = replace(task.map, items=replace_references(task.map.items, shared_ref), inputs=replace_references(task.map.inputs, shared_ref)) if task.map else None
            collected = replace(task.collect, inputs=tuple(shared_ref(ref) for ref in task.collect.inputs)) if task.collect else None
            condition = replace(task.condition, task=replacements.get(task.condition.task, task.condition.task)) if task.condition else None
            tasks.append(replace(task, inputs=replace_references(task.inputs, shared_ref), parameters=replace_references(task.parameters, shared_ref),
                dependencies=tuple(dict.fromkeys(replacements.get(dep, dep) for dep in task.dependencies)), map=mapped, collect=collected, condition=condition))
        declared_outputs = replace_references(declared_outputs, shared_ref)
    else:
        tasks = physical
    scopes = [replace(item, outputs=replace_references(item.outputs, unalias)) for item in scopes]
    if replacements:
        scopes = [replace(item, outputs=replace_references(item.outputs, shared_ref),
                          required_checks=tuple(replacements.get(key,key) for key in item.required_checks),
                          required_effects=tuple(replacements.get(key,key) for key in item.required_effects)) for item in scopes]
    identity = plan_identity(definition.scenario_id, tasks, declared_outputs, scopes, definition.policy, root_kind)
    return ExecutionPlan(identity, definition.scenario_id, tuple(tasks), declared_outputs, tuple(scopes), definition.policy, root_kind)


def _map_ports(mapped,catalog):
    from .plan import CanonicalMapTemplate
    if isinstance(mapped.body,CanonicalMapTemplate):
        snapshot = getattr(catalog,"snapshot",None)
        if snapshot is None or snapshot.fingerprint != mapped.body.catalog_fingerprint or mapped.body_fingerprint != snapshot.fingerprint:
            raise CompositionError("composition.method_changed")
        from stratbox.shared.data.processing import DataContract
        definition = snapshot.definition(mapped.body.capability_id)
        return tuple(OutputPort(name,port.schema or DataContract("capability.value"),
            qualifications=port.qualifications,coverage=port.expected_coverage,
            collection=port.collection) for name,port in definition.outputs.items())
    probe = compile_workflow(mapped.body,catalog,
        inputs={key:_DeferredInput(key,contract) for key,contract in mapped.body.inputs.items()},_defer=True)
    if probe.plan_id != mapped.body_fingerprint:
        raise CompositionError("composition.method_changed")
    return _plan_ports(probe,catalog)


def _plan_ports(plan, catalog):
    ports = []
    for name, ref in plan.outputs.items():
        if not isinstance(ref, PlanOutputRef):
            raise CompositionError("composition.map_output_reference_required")
        task = plan.task(ref.task)
        if task.operation_id:
            original = next(p for p in catalog.get(task.operation_id).processing.outputs if p.name == ref.port)
        elif task.collect:
            original = OutputPort(name, task.collect.contract, outcomes=frozenset({"succeeded", "partial"}) if task.collect.allow_partial else frozenset({"succeeded"}))
        else:
            original = next(p for p in _map_ports(task.map,catalog) if p.name == ref.port)
        ports.append(replace(original, name=name))
    return tuple(ports)


def _resolve_expansion_value(value, resolver):
    if resolver is None:
        if tuple(iter_references(value)):
            raise CompositionError("composition.expansion_resolution_required")
        return value
    resolved = resolver(value)
    if tuple(iter_references(resolved)):
        raise CompositionError("composition.expansion_reference_unresolved")
    return resolved


def _selector_values(value):
    """Unwrap control values only; data and parameter evidence stays typed."""
    if isinstance(value,(PreparedInput,ProjectedOutput)):
        return _selector_values(value.value)
    if isinstance(value,Mapping):
        return {key:_selector_values(item) for key,item in value.items()}
    if isinstance(value,tuple):
        return tuple(_selector_values(item) for item in value)
    if isinstance(value,list):
        return [_selector_values(item) for item in value]
    return value


def expand_map_item(plan, task, key, value, catalog, *,
                    resolve_value: ExpansionValueResolver | None = None) -> ExecutionPlan:
    """Materialize one admitted map item; the runtime owns its window credit."""
    if task.map is None:
        raise CompositionError("composition.map_required")
    if not isinstance(key, str) or not key:
        raise CompositionError("composition.invalid_item")
    from .plan import CanonicalMapTemplate
    if isinstance(task.map.body,CanonicalMapTemplate):
        _map_ports(task.map,catalog)
        from urllib.parse import quote
        from .prepare import prepare_invocation
        encoded = quote(key,safe="") if key not in {".",".."} else key.replace(".","%2E")
        arguments = dict(_resolve_expansion_value(task.map.inputs,resolve_value))
        parameters = arguments.pop("$parameters",{})
        arguments[task.map.item_input] = _resolve_expansion_value(value,resolve_value)
        selection = _selector_values(_resolve_expansion_value(task.map.body.selection,resolve_value))
        return prepare_invocation(task.map.body.capability_id,catalog.snapshot,catalog,
            inputs=arguments,parameters=parameters,outputs=task.map.body.outputs,selection=selection,
            _prefix=task.task_id + "/" + encoded)
    probe = compile_workflow(task.map.body, catalog,
        inputs={name: _DeferredInput(name, contract) for name, contract in task.map.body.inputs.items()}, _defer=True)
    if probe.plan_id != task.map.body_fingerprint:
        raise CompositionError("composition.method_changed")
    # Encode arbitrary manifest keys without letting them change scope paths.
    from urllib.parse import quote
    encoded_key = quote(key, safe="") if key not in {".", ".."} else key.replace(".", "%2E")
    prefix = task.task_id + "/" + encoded_key
    arguments = dict(_resolve_expansion_value(task.map.inputs,resolve_value))
    arguments[task.map.item_input] = _resolve_expansion_value(value,resolve_value)
    return compile_workflow(task.map.body, catalog, inputs=arguments, prefix=prefix)


def _validate_condition(condition, index, catalog, scopes=None):
    """Check declared value paths; conditions never evaluate Python code."""
    if condition.port is None:
        return
    from typing import Any, Union, get_args, get_origin
    from types import UnionType
    from collections.abc import Mapping as MappingABC
    from stratbox.core.execution.handoff import request_type_hints, _matches
    reference = getattr(condition,"reference",None)
    if isinstance(reference,ScopeOutputRef):
        scope = (scopes or {}).get(reference.scope_id)
        if scope is None or reference.port not in scope.output_contracts:
            raise CompositionError("composition.output_unknown")
        contract = scope.output_contracts[reference.port]
        candidates = [contract.value_type]
        path = tuple(part for part in condition.field.split(".") if part)
    else:
        candidates = None
    producer = index[condition.task]
    if candidates is None and producer.operation_id is None:
        # A map aggregate has per-item states and must be explicitly collected.
        if producer.map is not None:
            raise CompositionError("composition.condition_requires_operation")
        if condition.field:
            raise CompositionError("composition.condition_field_unknown")
        return
    if candidates is None:
        definition = catalog.get(producer.operation_id)
        output = next((p for p in definition.processing.outputs if p.name == condition.port), None)
        if output is None:
            raise CompositionError("composition.output_unknown")
        candidates = list(definition.value_type if isinstance(definition.value_type, tuple) else (definition.value_type,))
        path = tuple(p for p in (output.path + "." + condition.field).split(".") if p)
    for segment in path:
        next_candidates = []
        for kind in candidates:
            origin = get_origin(kind)
            variants = get_args(kind) if origin in (Union, UnionType) else (kind,)
            for variant in variants:
                origin = get_origin(variant)
                if variant is Any:
                    raise CompositionError("composition.condition_field_untyped")
                if origin is not None and isinstance(origin, type) and issubclass(origin, MappingABC):
                    arguments = get_args(variant)
                    if len(arguments) != 2 or arguments[0] is not str:
                        raise CompositionError("composition.condition_field_untyped")
                    next_candidates.append(arguments[1])
                elif isinstance(variant, type) and is_dataclass(variant):
                    annotation = request_type_hints(variant).get(segment)
                    if annotation is None:
                        raise CompositionError("composition.condition_field_unknown")
                    next_candidates.append(annotation)
                else:
                    raise CompositionError("composition.condition_field_unknown")
        candidates = next_candidates
    if not any(_matches(condition.equals, kind) for kind in candidates):
        raise CompositionError("composition.condition_value_type_mismatch")


def validate_plan(plan, catalog):
    """Re-admit a retained plan before submission, including its exact identity.

    Codec loading is data reconstruction only. This check resolves the current
    operation catalog and rejects stale methods, malformed graphs and changed
    input content before any effectful call can be admitted.
    """
    if not isinstance(plan, ExecutionPlan) or not isinstance(plan.tasks, tuple):
        raise CompositionError("composition.plan_required")
    identity = plan_identity(plan.definition_id, plan.tasks, plan.outputs, plan.scopes, plan.policy, plan.root_kind, plan.selected_bindings)
    if identity != plan.plan_id:
        raise CompositionError("composition.plan_identity_mismatch")
    if plan.policy not in {"continue", "fail_fast"}:
        raise CompositionError("composition.invalid_policy")
    index = {task.task_id: task for task in plan.tasks}
    if len(index) != len(plan.tasks):
        raise CompositionError("composition.duplicate_task")
    scopes = {scope.scope_id for scope in plan.scopes}
    if len(scopes) != len(plan.scopes):
        raise CompositionError("composition.duplicate_scope")
    if plan.root_kind not in {"command", "operation", "scenario", "cascade"}:
        raise CompositionError("composition.invalid_kind")
    scope_index = {scope.scope_id:scope for scope in plan.scopes}
    for scope in plan.scopes:
        if scope.parent_id is not None and scope.parent_id not in scope_index:
            raise CompositionError("composition.invalid_scope")
        if set((*scope.required_checks,*scope.required_effects)) - index.keys():
            raise CompositionError("composition.task_unknown")
    try:
        tuple(TopologicalSorter({scope.scope_id: (() if scope.parent_id is None else (scope.parent_id,))
                                 for scope in plan.scopes}).static_order())
    except CycleError:
        raise CompositionError("composition.cycle") from None
    snapshot = getattr(catalog,"snapshot",None)
    if plan.selected_bindings and snapshot is None:
        raise CompositionError("composition.catalog_snapshot_required")
    for scope_id, binding in plan.selected_bindings.items():
        if scope_id not in scope_index:
            raise CompositionError("composition.invalid_scope")
        definition = snapshot.definition(binding["capability_id"])
        identities = binding["identities"]
        if definition.fingerprint != identities.get("definition"):
            raise CompositionError("composition.definition_changed")
        for key in ("method","profile"):
            identifier = binding.get(key + "_id")
            if identifier is not None and getattr(snapshot,key)(identifier).fingerprint != identities.get(key):
                raise CompositionError("composition.method_changed")
        for key, fingerprint in identities.items():
            if key.startswith("schema:") and snapshot.schema(key[len("schema:"):]).fingerprint != fingerprint:
                raise CompositionError("composition.schema_changed")
            if key.startswith("reference:") and declaration_fingerprint(snapshot.reference(key[len("reference:"):])) != fingerprint:
                raise CompositionError("composition.reference_changed")
    for binding in plan.selected_bindings.values():
        snapshot.validate_binding(binding)
    definitions = {}
    for task in plan.tasks:
        if task.scope_id not in scopes or not task.task_id.startswith(task.scope_id + "/"):
            raise CompositionError("composition.invalid_scope")
        if sum((task.operation_id is not None, task.map is not None, task.collect is not None, task.acceptance_scope is not None)) != 1:
            raise CompositionError("composition.invalid_task")
        if set(task.dependencies) - set(index) or len(set(task.dependencies)) != len(task.dependencies):
            raise CompositionError("composition.task_unknown")
        references = (*iter_references(task.inputs), *iter_references(task.parameters),
                      *iter_references(task.map.items if task.map else ()),
                      *iter_references(task.map.inputs if task.map else ()),
                      *iter_references(getattr(task.map.body,"selection",{}) if task.map else ()),
                      *iter_references(task.collect.inputs if task.collect else ()))
        required_dependencies = {ref.task for ref in references}
        for condition in task_conditions(task):
            required_dependencies.add(condition.task)
        if not required_dependencies <= set(task.dependencies):
            raise CompositionError("composition.dependency_missing")
        if task.acceptance_scope is not None and task.acceptance_scope not in scopes:
            raise CompositionError("composition.invalid_scope")
        if task.operation_id:
            definition = catalog.get(task.operation_id)
            _require_atomic(definition)
            definitions[task.operation_id] = definition
            work = None if definition.method_refs else catalog.resolve(task.operation_id)[1]
            if (definition.method_id != task.method_id or method_descriptor(definition, work=work).identity.sha256 != task.method_fingerprint):
                raise CompositionError("composition.method_changed")
            if task.share_key and definition.possible_effects:
                raise CompositionError("composition.effect_sharing_forbidden")
            expected = _source_parameters(catalog, task.source, definition, dict(task.parameters))
            if expected != task.parameters:
                raise CompositionError("composition.source_parameters_missing")
            semantics = definition.processing
            if semantics is None or set(task.inputs) - {port.name for port in semantics.inputs}:
                raise CompositionError("handoff.input_unknown")
            if any(port.required and port.name not in task.inputs for port in semantics.inputs):
                raise CompositionError("handoff.input_required")
            if set(task.parameters) - set(semantics.parameters):
                raise CompositionError("handoff.parameter_unknown")
            if set(semantics.required_parameters) - set(task.parameters):
                raise CompositionError("handoff.parameter_required")
            _validate_parameters(task, index, catalog)
            if task.capability_kind == "command" and task.scope_id in plan.selected_bindings:
                authored = snapshot.definition(task.operation_id)
                selected_binding = plan.selected_bindings[task.scope_id]
                if (task.reuse_contract != authored.reuse
                        or argument_identity(task.parameters) != argument_identity(selected_binding["parameters"])):
                    raise CompositionError("composition.command_policy_changed")
                basis = task.reuse_identity
                if basis is not None:
                    exact = dict(basis.binding_fingerprints)
                    if (task.work_identity != basis.fingerprint
                            or basis.command_id != authored.capability_id
                            or basis.implementation_revision != authored.revision + ":" + authored.implementation_ref
                            or basis.schema_fingerprint != declaration_fingerprint(authored.outputs)
                            or exact.get("implementation") != task.method_fingerprint
                            or any(exact.get(key) != value for key,value in selected_binding["identities"].items())):
                        raise CompositionError("composition.work_identity_changed")
                    ancestors = []
                    parent_id = scope_index[task.scope_id].parent_id
                    while parent_id is not None:
                        if parent_id in plan.selected_bindings:
                            ancestors.append(plan.selected_bindings[parent_id]["identities"])
                        parent_id = scope_index[parent_id].parent_id
                    for key,value in exact.items():
                        if key.startswith("specialization.") and not any(
                                ancestor.get(key[len("specialization."):]) == value for ancestor in ancestors):
                            raise CompositionError("composition.work_identity_changed")
                elif task.work_identity is not None or task.reuse_eligible:
                    raise CompositionError("composition.work_identity_changed")
        if task.map:
            _map_ports(task.map,catalog)
        for condition in task_conditions(task):
            if condition.task not in index:
                raise CompositionError("composition.task_unknown")
            _validate_condition(condition,index,catalog,scope_index)
    try:
        tuple(TopologicalSorter({task.task_id: task.dependencies for task in plan.tasks}).static_order())
    except CycleError:
        raise CompositionError("composition.cycle") from None

    def output_port(ref):
        if isinstance(ref,ScopeOutputRef):
            scope = scope_index.get(ref.scope_id)
            if scope is None or ref.port not in scope.output_contracts:
                raise CompositionError("composition.output_unknown")
            expected_task = scope.scope_id + ("/work" if scope.kind == "command" else "/accept")
            if ref.task != expected_task or ref.task not in index:
                raise CompositionError("composition.scope_output_owner_mismatch")
            from stratbox.shared.data.processing import DataContract
            contract = scope.output_contracts[ref.port]
            return OutputPort(ref.port,contract.schema or DataContract("capability.value"),
                qualifications=contract.qualifications,coverage=contract.expected_coverage,
                collection=contract.collection,outcomes=contract.outcomes)
        if ref.task not in index:
            raise CompositionError("composition.task_unknown")
        task = index[ref.task]
        if ref.item is not None and task.map is None:
            raise CompositionError("composition.item_requires_map")
        if task.operation_id:
            ports = definitions[task.operation_id].processing.outputs
        elif task.collect:
            ports = (OutputPort("value", task.collect.contract, outcomes=frozenset({"succeeded", "partial"}) if task.collect.allow_partial else frozenset({"succeeded"})),)
        else:
            ports = _map_ports(task.map,catalog)
        port = next((port for port in ports if port.name == ref.port), None)
        if port is None:
            raise CompositionError("composition.output_unknown")
        return port

    for task in plan.tasks:
        for ref in (*iter_references(task.inputs), *iter_references(task.parameters),
                    *iter_references(task.map.items if task.map else ()),
                    *iter_references(task.map.inputs if task.map else ()),
                    *iter_references(getattr(task.map.body,"selection",{}) if task.map else ())):
            output_port(ref)
        if task.operation_id:
            definition = definitions[task.operation_id]
            inputs = {port.name: port for port in definition.processing.inputs}
            for name, value in task.inputs.items():
                if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
                    if index[value.task].map is not None and value.item is None:
                        raise CompositionError("composition.map_collect_required")
                    if not compatible_ports(output_port(value), inputs[name]):
                        raise CompositionError("processing.schema_mismatch")
                else:
                    supplied = adapt_input(value)
                    assessment = assess_input(inputs[name], supplied.contract, outcome=supplied.outcome,
                                              qualifications=supplied.qualifications, coverage=supplied.coverage)
                    if not assessment.compatible:
                        raise CompositionError(assessment.reasons[0])
        if task.collect:
            if any((output_port(value).contract if isinstance(value,(PlanOutputRef,ScopeOutputRef)) else adapt_input(value).contract)
                   != task.collect.element_contract for value in task.collect.inputs):
                raise CompositionError("processing.schema_mismatch")
    for task in plan.tasks:
        for condition in task_conditions(task):
            reference = getattr(condition,"reference",None)
            if reference is not None:
                if not isinstance(reference,(PlanOutputRef,ScopeOutputRef)) or reference.task != condition.task:
                    raise CompositionError("composition.condition_reference_mismatch")
                if condition.port is not None and reference.port != condition.port:
                    raise CompositionError("composition.condition_reference_mismatch")
                output_port(reference)
    scope_output_graph = {}
    for scope in plan.scopes:
        scope_output_graph[scope.scope_id] = tuple(ref.scope_id for ref in iter_references(scope.outputs)
                                                   if isinstance(ref,ScopeOutputRef))
        for ref in iter_references(scope.outputs):
            output_port(ref)
    try:
        tuple(TopologicalSorter(scope_output_graph).static_order())
    except CycleError:
        raise CompositionError("composition.scope_output_cycle") from None
    for ref in iter_references(plan.outputs):
        output_port(ref)
    return plan


def _validate_parameters(task, index, catalog):
    from typing import Any, Union, get_args, get_origin
    from types import UnionType
    from stratbox.core.execution.handoff import request_type_hints, _matches
    definition = catalog.get(task.operation_id)
    hints = request_type_hints(definition.request_type)

    def alternatives(kind):
        return get_args(kind) if get_origin(kind) in (Union, UnionType) else (kind,)

    def assignable(source, target):
        if target is Any or source is Any:
            return True
        if get_origin(target) in (Union, UnionType):
            return any(assignable(source, option) for option in get_args(target))
        if get_origin(source) in (Union, UnionType):
            return all(assignable(option, target) for option in get_args(source))
        if source == target:
            return True
        if isinstance(source, type) and isinstance(target, type):
            if source in (bool, int, float, str, bytes) or target in (bool, int, float, str, bytes):
                return source is target
            return issubclass(source, target)
        return get_origin(source) == get_origin(target) and get_args(source) == get_args(target)

    for name, value in task.parameters.items():
        annotation = hints.get(name, Any)
        if isinstance(value, _DeferredInput):
            continue
        if isinstance(value, (PlanOutputRef,ScopeOutputRef)):
            producer = index[value.task]
            if producer.operation_id is None:
                continue
            source = catalog.get(producer.operation_id)
            output = next(port for port in source.processing.outputs if port.name == value.port)
            types = list(source.value_type if isinstance(source.value_type, tuple) else (source.value_type,))
            for segment in output.path.split(".") if output.path else ():
                projected = []
                for kind in types:
                    for variant in alternatives(kind):
                        if isinstance(variant, type) and is_dataclass(variant):
                            projected.append(request_type_hints(variant).get(segment, Any))
                        else:
                            projected.append(Any)
                types = projected
            if not all(assignable(kind, annotation) for kind in types):
                raise CompositionError("handoff.parameter_type_mismatch")
        elif not tuple(iter_references(value)) and not _matches(value, annotation):
            raise CompositionError("handoff.parameter_type_mismatch")
