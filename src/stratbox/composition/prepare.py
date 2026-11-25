"""Prepare four capability kinds into command work and acceptance scopes.

Resolution is restricted to the selected output/check/effect closure. Supplied
outputs are accepted inputs to this invocation and stop upstream expansion.
The returned plan is consumed by the ordinary execution session.
"""
from __future__ import annotations

from dataclasses import replace
from graphlib import TopologicalSorter, CycleError
from typing import Mapping

from stratbox.capabilities.model import (
    CommandDefinition, InputRef, ParameterRef, OutputRef, WorkIdentity, MapCall, CollectCall, FoldCall,
)
from stratbox.capabilities.model.definitions import declaration_fingerprint
from stratbox.capabilities.model.reuse import build_work_identity
from stratbox.core.execution.methods import method_descriptor
from stratbox.core.execution.values import argument_identity
from ._validation import CompositionError
from .models import PlanOutputRef, Condition, RetryPolicy, CollectSpec
from .plan import ExecutionPlan, CompiledTask, PlanScope, CompiledMap, CanonicalMapTemplate, ScopeOutputRef
from .compiler import plan_identity, iter_references
from .requests import InvocationRequest, GoalRequest

_ALLOWED = {"operation": {"command"}, "scenario": {"operation", "scenario"}, "cascade": {"scenario"}}
_MISSING = object()


def _refs(value):
    if isinstance(value, OutputRef):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _refs(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _refs(item)


def _parameter_names(value):
    if isinstance(value,ParameterRef):
        yield value.name
    elif isinstance(value,Mapping):
        for item in value.values():
            yield from _parameter_names(item)


def _input_names(value):
    if isinstance(value, InputRef):
        yield value.name
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _input_names(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _input_names(item)
    elif isinstance(value,(tuple,list)):
        for item in value:
            yield from _parameter_names(item)


def _node_values(call):
    return (call.inputs,getattr(call,"parameters",{}),getattr(call,"items",()),getattr(call,"selection",{}),
            getattr(call,"initial",None),getattr(call,"retry",None))


def prepare_invocation(definition_or_id, snapshot, runtime_catalog, *, inputs=None,
                       parameters=None, outputs=None, supplied_outputs=None,
                       method_id=None, profile_id=None, group_id=None, selection=None, recipe_id=None, _prefix=None):
    """Resolve and lower exact identities without executing a handler.

    ``supplied_outputs`` addresses a named root output (``value``), or a
    qualified call output (``scenario/extract.value``). Such values do not
    discharge separately declared checks or effects.
    """
    if isinstance(definition_or_id, InvocationRequest):
        request = definition_or_id
        if any(value is not None for value in (inputs, parameters, outputs, supplied_outputs, method_id, profile_id, group_id,selection,recipe_id)):
            raise CompositionError("composition.request_already_bound")
        return prepare_invocation(request.capability_id, snapshot, runtime_catalog,
            inputs=request.inputs, parameters=request.parameters, outputs=request.outputs,
            supplied_outputs=request.supplied_outputs, method_id=request.method_id,
            profile_id=request.profile_id, group_id=request.group_id,selection=request.selection,recipe_id=request.recipe_id)
    root = snapshot.definition(definition_or_id) if isinstance(definition_or_id, str) else definition_or_id
    if not hasattr(root, "kind") or root.kind not in {"command", "operation", "scenario", "cascade"}:
        raise CompositionError("composition.definition_required")
    if not isinstance(definition_or_id, str):
        # Local definitions use the same catalog admission and resolution rules.
        try:
            existing = snapshot.definition(root.capability_id)
        except (KeyError, ValueError):
            existing = None
        if existing is None or existing.fingerprint != root.fingerprint:
            from stratbox.capabilities.catalog import CatalogContribution
            if hasattr(runtime_catalog,"admit_local"):
                snapshot = runtime_catalog.admit_local(root)
            else:
                snapshot = snapshot.overlay(CatalogContribution(definitions=(root,)),
                                            replace_ids=(root.capability_id,) if existing is not None else ())
    selected = tuple(root.outputs) if outputs is None else ((outputs,) if isinstance(outputs, str) else tuple(outputs))
    if len(set(selected)) != len(selected) or set(selected) - set(root.outputs):
        raise CompositionError("composition.output_unknown")
    supplied = dict(supplied_outputs or {})
    tasks, scopes, bindings = [], [], {}
    producers = {}
    scope_outputs = {}

    def identity_value(value):
        if isinstance(value,ScopeOutputRef):
            return identity_value(scope_outputs[value.scope_id][value.port])
        if isinstance(value,PlanOutputRef):
            producer = producers.get(value.task)
            return ("producer", producer.work_identity if producer and producer.work_identity else value.task,value.port,value.item)
        if isinstance(value,Mapping):
            return {key:identity_value(item) for key,item in value.items()}
        if isinstance(value,(tuple,list)):
            return tuple(identity_value(item) for item in value)
        return value

    def retained(scope, name, *, root_output=False):
        keys = (f"{scope}.{name}", name) if root_output else (f"{scope}.{name}",)
        for key in keys:
            if key in supplied:
                return supplied[key]
        return _MISSING

    def lower(definition, scope, arguments, semantic_parameters, chosen_outputs, *, parent=None,
              required=True, method=None, profile=None, group=None, ancestry=(), external_dependencies=(), inherited_conditions=(),selection_context=None,recipe=None,binding_context=None,retry_override=None,expected_binding=None):
        if definition.capability_id in ancestry:
            raise CompositionError("composition.cycle")
        if set(arguments) - set(definition.inputs):
            raise CompositionError("composition.input_unknown")
        binding = snapshot.resolve(definition.capability_id, method_id=method, profile_id=profile,
                                   group_id=group, parameters=semantic_parameters,selection=selection_context,recipe_id=recipe)
        if expected_binding and any(binding.identities.get(name) != identity for name, identity in expected_binding.items()):
            raise CompositionError("composition.binding_reference_changed")
        chosen_outputs = tuple(dict.fromkeys((*chosen_outputs,*definition.acceptance.coherent_outputs)))
        parameters_bound = dict(binding.parameters)
        identities = dict(binding.identities)
        bindings[scope] = binding.projection()
        position = len(scopes)
        scopes.append(PlanScope(scope, definition.capability_id, parent,
            getattr(definition, "expenditure", {}), kind=definition.kind, required=required,
            output_contracts={name:definition.outputs[name] for name in chosen_outputs},
            acceptance=definition.acceptance,membership=getattr(definition,"membership",None),conditions=inherited_conditions))
        if isinstance(definition, CommandDefinition):
            allowed_parameters = set(definition.parameters) | set(definition.fixed) | set(definition.required_parameters)
            if set(parameters_bound) - allowed_parameters:
                raise CompositionError("handoff.parameter_unknown")
            if set(definition.required_parameters) - parameters_bound.keys():
                raise CompositionError("composition.parameter_required")
            concrete_inputs = dict(arguments)
            for name, port in definition.inputs.items():
                if not port.required and concrete_inputs.get(name, _MISSING) is None:
                    concrete_inputs.pop(name, None)
                if port.required and name not in concrete_inputs:
                    raise CompositionError("composition.input_required")
                if name in concrete_inputs and not tuple(iter_references(concrete_inputs[name])):
                    from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
                    value = concrete_inputs[name]
                    port.validate(value.value if isinstance(value, (PreparedInput, ProjectedOutput)) else value)
                    if not isinstance(value, (PreparedInput, ProjectedOutput)):
                        from stratbox.core.execution.handoff import prepare_input
                        from stratbox.shared.data.processing import DataContract
                        concrete_inputs[name] = prepare_input(value,port.schema or DataContract("capability.value"))
            old_definition = runtime_catalog.get(definition.capability_id)
            work = None if old_definition.method_refs else runtime_catalog.resolve(definition.capability_id)[1]
            fingerprint = method_descriptor(old_definition, work=work).identity.sha256
            task_id = scope + "/work"
            dependencies = tuple(dict.fromkeys((*external_dependencies,
                *(ref.task for ref in iter_references((concrete_inputs, parameters_bound))))))
            reuse = (definition.reuse.eligible
                     and (not definition.effects or definition.reuse.observation_scoped
                          and definition.effects <= {"network.receive"}))
            work_id = None
            reuse_identity = None
            if reuse:
                leaf_identities = {**(binding_context or {}),**binding.identities,"implementation":fingerprint}
                reuse_identity = build_work_identity(definition.capability_id,
                    definition.revision + ":" + definition.implementation_ref,
                    input_identities=tuple((name,argument_identity(identity_value(value)).sha256)
                                           for name,value in concrete_inputs.items()),
                    parameters_fingerprint=argument_identity(identity_value(parameters_bound)).sha256,
                    binding_identities=leaf_identities,
                    schema_fingerprint=declaration_fingerprint(definition.outputs))
                work_id = reuse_identity.fingerprint
            retry = retry_override or definition.retry
            task = CompiledTask(task_id, definition.capability_id, concrete_inputs, parameters_bound,
                dependencies, scope, required, inherited_conditions[0] if len(inherited_conditions) == 1 else None,
                resources=definition.resources,
                retry=RetryPolicy(retry.max_attempts, retry.delay, retry.retry_codes),
                method_id=old_definition.method_id, method_fingerprint=fingerprint,
                capability_kind="command", work_identity=work_id, reuse_eligible=reuse,conditions=inherited_conditions,
                reuse_contract=definition.reuse,reuse_identity=reuse_identity)
            tasks.append(task)
            producers[task_id] = task
            actual_id = task_id
            named = {name:PlanOutputRef(actual_id,name) for name in chosen_outputs}
            scopes[position] = replace(scopes[position], outputs=named)
            scope_outputs[scope] = named
            owned = {name:ScopeOutputRef(scope,name,actual_id) for name in named}
            return owned, actual_id, (actual_id,)

        body = binding.body
        if body is None:
            raise CompositionError("composition.body_required")
        call_index = {call.step_id:call for call in body.steps}
        allowed = _ALLOWED[definition.kind]
        # Body shape and references are metadata checks, independent of providers.
        graph = {}
        for call in body.steps:
            if not isinstance(call,CollectCall):
                child = snapshot.definition(call.capability_id)
                if child.kind not in allowed:
                    raise CompositionError("composition.invalid_body_kind")
                if isinstance(call,MapCall) and child.kind != "scenario":
                    raise CompositionError("composition.invalid_map_body_kind")
            dependencies = {ref.step for ref in _refs(_node_values(call))} | set(call.depends_on)
            condition = getattr(call,"condition",None)
            if condition is not None:
                dependencies.add(condition.step)
            if dependencies - call_index.keys():
                raise CompositionError("composition.task_unknown")
            graph[call.step_id] = dependencies
        for ref in _refs(body.outputs):
            if ref.step not in call_index:
                raise CompositionError("composition.task_unknown")
        try:
            order = tuple(TopologicalSorter({key:tuple(sorted(dependencies)) for key,dependencies in graph.items()}).static_order())
        except CycleError:
            raise CompositionError("composition.cycle") from None

        def cached_ref(ref):
            return retained(scope + "/" + ref.step, ref.port)

        selected_values = {}
        for name in chosen_outputs:
            cached = retained(scope, name, root_output=parent is None)
            if cached is not _MISSING:
                definition.outputs[name].validate(getattr(cached,"value",cached))
                selected_values[name] = cached
                original = body.outputs.get(name)
                if isinstance(original,OutputRef):
                    supplied.setdefault(f"{scope}/{original.step}.{original.port}",cached)
            elif name in body.outputs:
                selected_values[name] = body.outputs[name]
            else:
                raise CompositionError("composition.output_unknown")
        roots = {ref.step for ref in _refs(selected_values) if cached_ref(ref) is _MISSING}
        check_roots = tuple(dict.fromkeys((*body.required_checks,*definition.acceptance.required_checks)))
        effect_roots = tuple(dict.fromkeys((*body.required_effects,*definition.acceptance.required_effects)))
        roots.update((*check_roots,*effect_roots,*body.required_completions))
        if roots - call_index.keys():
            raise CompositionError("composition.task_unknown")
        keep, pending = set(), list(roots)
        while pending:
            key = pending.pop()
            if key in keep:
                continue
            keep.add(key)
            call = call_index[key]
            pending.extend(call.depends_on)
            pending.extend(ref.step for ref in _refs(_node_values(call)) if cached_ref(ref) is _MISSING)
            if getattr(call,"condition",None) is not None:
                pending.append(call.condition.step)
        # Validate the selected functional boundary before a permissive child
        # can consume it. Unused branches create no input obligations.
        from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
        used_inputs = set(_input_names((selected_values,
            tuple(_node_values(call_index[key]) for key in keep))))
        for name in used_inputs:
            port = definition.inputs[name]
            if name not in arguments:
                if port.required:
                    raise CompositionError("composition.input_required")
                continue
            incoming = arguments[name]
            if incoming is None and not port.required:
                continue
            if tuple(iter_references(incoming)):
                continue
            if isinstance(incoming, (PreparedInput, ProjectedOutput)):
                if port.schema is not None and incoming.contract not in (port.schema, *port.alternatives):
                    raise CompositionError("processing.schema_mismatch")
                if incoming.outcome not in port.outcomes:
                    raise CompositionError("processing.outcome_not_accepted")
                if not port.qualifications <= incoming.qualifications:
                    raise CompositionError("processing.qualification_missing")
                if not port.expected_coverage <= incoming.coverage:
                    raise CompositionError("processing.coverage_missing")
                incoming = incoming.value
            else:
                from stratbox.shared.data.assessment import value_evidence
                evidence = value_evidence(incoming)
                if not port.qualifications <= evidence.qualifications:
                    raise CompositionError("processing.qualification_missing")
                facts = evidence.coverage.facts if evidence.coverage is not None else frozenset()
                if not port.expected_coverage <= facts:
                    raise CompositionError("processing.coverage_missing")
            port.validate(incoming)
        resolved, completions, members = {}, {}, {}

        def value_of(value):
            if isinstance(value, InputRef):
                if value.name not in arguments:
                    if value.name in definition.inputs and not definition.inputs[value.name].required:
                        return None
                    raise CompositionError("composition.input_required")
                return arguments[value.name]
            if isinstance(value, ParameterRef):
                if value.name not in parameters_bound:
                    raise CompositionError("composition.parameter_required")
                result = parameters_bound[value.name]
                for field in value.path.split(".") if value.path else ():
                    try:
                        result = result[field] if isinstance(result, Mapping) else getattr(result, field)
                    except (KeyError, AttributeError, TypeError):
                        raise CompositionError("composition.parameter_path_unavailable") from None
                return result
            if isinstance(value, OutputRef):
                cached = cached_ref(value)
                if cached is not _MISSING:
                    return cached
                if value.step not in resolved or value.port not in resolved[value.step]:
                    raise CompositionError("composition.output_unknown")
                return resolved[value.step][value.port]
            if isinstance(value, Mapping):
                return {key:value_of(item) for key,item in value.items()}
            if isinstance(value, tuple):
                return tuple(value_of(item) for item in value)
            if isinstance(value, list):
                return [value_of(item) for item in value]
            return value

        start = len(tasks)
        for key in order:
            if key not in keep:
                continue
            call = call_index[key]
            child = None if isinstance(call,CollectCall) else snapshot.definition(call.capability_id)
            declared_ports = {"value":call.contract} if isinstance(call,CollectCall) else child.outputs
            wanted = {ref.port for ref in _refs((selected_values,
                       *[_node_values(call_index[other]) for other in keep]))
                      if ref.step == key and cached_ref(ref) is _MISSING}
            # Obligations without a data consumer need their full completion contract.
            if not wanted:
                wanted = set(declared_ports)
            unknown = wanted - declared_ports.keys()
            if unknown:
                raise CompositionError("composition.output_unknown")
            dependency_keys = set(call.depends_on)
            dependency_keys.update(ref.step for ref in _refs(_node_values(call)) if cached_ref(ref) is _MISSING)
            conditions = inherited_conditions
            if getattr(call,"condition",None) is not None:
                condition_def = call.condition
                dependency_keys.add(condition_def.step)
                condition_ref = value_of(OutputRef(condition_def.step,condition_def.port))
                if not isinstance(condition_ref,(PlanOutputRef,ScopeOutputRef)):
                    raise CompositionError("composition.condition_reference_required")
                local_condition = Condition(condition_ref.task,condition_def.statuses,
                    None if condition_def.statuses else condition_ref.port,
                    condition_def.field,condition_def.equals,reference=condition_ref)
                conditions = (*inherited_conditions,local_condition)
            extra = tuple(dict.fromkeys((*external_dependencies,
                *(completions[name] for name in sorted(dependency_keys)),
                *(condition.task for condition in conditions))))
            condition = conditions[0] if len(conditions) == 1 else None
            call_selection = {**(selection_context or {}),**value_of(getattr(call,"selection",{}))}
            if isinstance(call, FoldCall):
                items = value_of(call.items)
                if not isinstance(items, (tuple, list)):
                    raise CompositionError("composition.fold_frozen_items_required")
                if len(items) > call.max_items:
                    raise CompositionError("composition.fold_item_limit")
                state = value_of(call.initial)
                previous = extra
                folded_children = []
                override = value_of(call.retry)
                if override is not None:
                    from stratbox.capabilities.model.graph import RetryPolicy as AuthoredRetry
                    if isinstance(override, Mapping):
                        if set(override) - {"max_attempts", "delay", "retry_codes"}:
                            raise CompositionError("composition.fold_retry_invalid")
                        override = AuthoredRetry(**dict(override))
                    if not isinstance(override, AuthoredRetry):
                        raise CompositionError("composition.fold_retry_invalid")
                override = override or retry_override
                for index, item in enumerate(items):
                    child_inputs = {**value_of(call.inputs), call.item_input: item, call.state_input: state}
                    folded, completion, descendants = lower(child, scope + "/" + key + "/item_" + str(index),
                        child_inputs, value_of(call.parameters), (call.state_output,), parent=scope,
                        required=required and call.required, ancestry=(*ancestry, definition.capability_id),
                        external_dependencies=previous, inherited_conditions=conditions,
                        selection_context=call_selection, binding_context=binding_context,
                        retry_override=override)
                    state = folded[call.state_output]
                    previous = (completion,)
                    folded_children.extend(descendants)
                if not items:
                    if not isinstance(state, (PlanOutputRef, ScopeOutputRef)):
                        raise CompositionError("composition.fold_empty_requires_initial_producer")
                    completion = state.task
                resolved[key],completions[key],members[key] = {"value": state},completion,tuple(folded_children)
                continue
            if isinstance(call,MapCall):
                if call.item_input in call.inputs:
                    raise CompositionError("composition.map_item_conflict")
                template = CanonicalMapTemplate(child.capability_id,tuple(child.outputs),snapshot.fingerprint,call_selection)
                mapped = CompiledMap(template,value_of(call.items),call.item_input,call.key_field,call.window,
                    {**value_of(call.inputs),"$parameters":value_of(call.parameters)},call.allow_partial,
                    snapshot.fingerprint,call.max_items)
                task_id = scope + "/" + key
                tasks.append(CompiledTask(task_id,None,{},{},extra,scope,required and call.required,
                                          condition=condition,map=mapped,capability_kind="scenario",conditions=conditions))
                resolved[key],completions[key],members[key] = {"value":PlanOutputRef(task_id)},task_id,(task_id,)
                continue
            if isinstance(call,CollectCall):
                from stratbox.core.execution.handoff import prepare_input,PreparedInput,ProjectedOutput
                from stratbox.shared.data.processing import DataContract
                values = tuple(value_of(ref) for ref in call.inputs)
                elements = tuple(value if isinstance(value,(PlanOutputRef,ScopeOutputRef,PreparedInput,ProjectedOutput)) else
                    prepare_input(value,call.element_contract.schema or DataContract("capability.value")) for value in values)
                collected = CollectSpec(elements,call.contract.schema or DataContract("capability.collection"),
                    call.element_contract.schema or DataContract("capability.value"),call.allow_partial,call.allow_empty)
                task_id = scope + "/" + key
                tasks.append(CompiledTask(task_id,None,{},{},extra,scope,required and call.required,
                                          condition=condition,collect=collected,capability_kind="scenario",conditions=conditions))
                resolved[key],completions[key],members[key] = {"value":PlanOutputRef(task_id)},task_id,(task_id,)
                continue
            significant_context = dict(binding_context or {})
            if tuple(_parameter_names(_node_values(call))):
                significant_context.update({"specialization." + name:value for name,value in binding.identities.items()
                    if name in {"method","profile","group"} or name.startswith(("schema:","reference:"))})
            named, completed, children = lower(child, scope + "/" + key,
                value_of(call.inputs),value_of(call.parameters),tuple(name for name in child.outputs if name in wanted),
                parent=scope,required=required and call.required,method=call.method_id,
                profile=call.profile_id,group=call.group_id,ancestry=(*ancestry,definition.capability_id),
                external_dependencies=extra,inherited_conditions=conditions,selection_context=call_selection,
                binding_context=significant_context,retry_override=retry_override,
                expected_binding=call.binding_identities)
            resolved[key],completions[key],members[key] = named,completed,children
        named = {name:value_of(value) for name,value in selected_values.items()}
        checks = tuple(completions[key] for key in check_roots)
        effects = tuple(completions[key] for key in effect_roots)
        scopes[position] = replace(scopes[position], outputs=named,required_checks=checks,required_effects=effects)
        dependencies = tuple(dict.fromkeys((*external_dependencies,*checks,*effects,
            *(completions[key] for key in body.required_completions),
            *(completions[key] for key in call_index if key in keep and call_index[key].required),
            *(ref.task for ref in iter_references(named)))))
        accept_id = scope + "/accept"
        tasks.append(CompiledTask(accept_id,None,{},{},dependencies,scope,required,
                                 condition=inherited_conditions[0] if len(inherited_conditions) == 1 else None,
                                 capability_kind=definition.kind,acceptance_scope=scope,conditions=inherited_conditions))
        scope_outputs[scope] = named
        owned = {name:ScopeOutputRef(scope,name,accept_id) for name in named}
        return owned,accept_id,tuple(task.task_id for task in tasks[start:])

    named,_,_ = lower(root,_prefix or root.capability_id,dict(inputs or {}),dict(parameters or {}),selected,
                      method=method_id,profile=profile_id,group=group_id,selection_context=dict(selection or {}),recipe=recipe_id)
    named = {name:value for name,value in named.items() if name in selected}
    policy = getattr(root,"policy","continue")
    identity = plan_identity(root.capability_id,tasks,named,scopes,policy,root.kind,bindings)
    return ExecutionPlan(identity,root.capability_id,tuple(tasks),named,tuple(scopes),policy,root.kind,bindings)


def prepare_goal(request, snapshot, runtime_catalog, **options):
    """Select a registered goal recipe and use exact invocation preparation."""
    if isinstance(request,str):
        request = GoalRequest(request,**options)
    elif options:
        raise CompositionError("composition.request_already_bound")
    if not isinstance(request,GoalRequest):
        raise CompositionError("composition.goal_required")
    recipe = snapshot.resolve_goal(request.goal,selection=request.selection,recipe_id=request.recipe_id)
    capability_id = recipe.capability_id
    parameters = dict(request.parameters)
    return prepare_invocation(capability_id,snapshot,runtime_catalog,inputs=request.inputs,
        parameters=parameters,outputs=request.outputs,supplied_outputs=request.supplied_outputs,selection=request.selection,recipe_id=recipe.recipe_id)
