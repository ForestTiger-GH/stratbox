"""Pure recursive validation and dependency completion for public plans.

References and acceptance guards are scheduling edges, including inside a
template. Branch-local namespaces remain separate. This owner performs no
provider access and never publishes a partially validated graph.
"""
from collections.abc import Mapping
from dataclasses import fields
from graphlib import CycleError, TopologicalSorter

from .models import PreparedPlan, TemplateInput, ValueRef


def _record(value, **changes):
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(value, field.name)))
    return result


def references(value):
    if isinstance(value, (ValueRef, TemplateInput)):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from references(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from references(item)
    elif type(value).__name__ == 'Condition':
        yield from references(value.value)


def output_names(task):
    if hasattr(task, 'command'):
        return frozenset(task.command.outputs)
    kind = getattr(task, 'kind', None)
    if kind in {'map', 'collect'}:
        return frozenset({'items', 'outcomes'})
    if kind == 'repeat':
        return frozenset({'state'})
    if kind == 'dispatch':
        return frozenset({task.output_port})
    raise ValueError('plan.unknown_task_kind')


def _acyclic(edges, code):
    try:
        tuple(TopologicalSorter(edges).static_order())
    except CycleError:
        raise ValueError(code) from None


def validate_plan(plan, *, external_ports=None, external_scopes=None,
                  template_inputs=(), capacities=None, max_depth=64, _depth=0):
    """Return a checked plan whose dependencies include every used reference.

    External ports are explicit captured parent dependencies, or existing tasks
    supplied by the atomic expansion owner. A public root has no such captures.
    """
    if not isinstance(plan, PreparedPlan):
        raise ValueError('plan.prepared_plan_required')
    if _depth > max_depth:
        raise ValueError('plan.template_depth')
    tasks = {task.task_id: task for task in plan.tasks}
    scopes = {scope.scope_id: scope for scope in plan.scopes}
    if len(tasks) != len(plan.tasks):
        raise ValueError('plan.duplicate_task')
    if len(scopes) != len(plan.scopes):
        raise ValueError('plan.duplicate_scope')
    if any(not isinstance(name, str) or not name for name in (*tasks, *scopes)):
        raise ValueError('plan.invalid_identity')
    outer_ports = dict(external_ports or {})
    ports = {**outer_ports, **{name: output_names(task) for name, task in tasks.items()}}
    all_scopes = {**dict(external_scopes or {}), **scopes}
    allowed_inputs = frozenset(template_inputs)

    def dependencies(value):
        result = set()
        for reference in references(value):
            if isinstance(reference, TemplateInput):
                if reference.name not in allowed_inputs:
                    raise ValueError('plan.unknown_template_input:' + reference.name)
            else:
                if reference.task_id not in ports:
                    raise ValueError('plan.unknown_dependency:' + reference.task_id)
                if reference.port not in ports[reference.task_id]:
                    raise ValueError('plan.unknown_output:' + reference.port)
                result.add(reference.task_id)
        return result

    def obligation(scope, name):
        if name in ports:
            return name
        qualified = scope.scope_id + '/' + name
        if qualified in ports:
            return qualified
        reference = scope.outputs.get(name)
        if isinstance(reference, ValueRef):
            return reference.task_id
        raise ValueError('plan.unknown_obligation:' + name)

    def guarded(guard):
        if guard.scope_id not in all_scopes:
            raise ValueError('plan.unknown_guard_scope')
        scope = all_scopes[guard.scope_id]
        if guard.port not in scope.outputs:
            raise ValueError('plan.unknown_guard_output')
        names = {guard.port}
        coherent = set(scope.acceptance.coherent_outputs)
        if names & coherent:
            names.update(coherent)
        for predicate in scope.acceptance.predicates:
            first = predicate.path.split('.', 1)[0] if predicate.path else None
            if first not in scope.outputs:
                names.update(scope.outputs)
        result = set().union(*(dependencies(scope.outputs[name]) for name in names))
        result.update(dependencies(scope.condition))
        result.update(obligation(scope, name) for name in (*scope.required_checks,
            *scope.acceptance.required_checks, *scope.acceptance.required_effects))
        return result

    def member_obligations(scope_id, visited=None):
        visited = set() if visited is None else visited
        if scope_id in visited:
            return set()
        visited.add(scope_id)
        scope = all_scopes[scope_id]
        result = set(scope.required_tasks)
        result.update(obligation(scope, name) for name in (*scope.required_checks,
            *scope.required_effects, *scope.acceptance.required_checks, *scope.acceptance.required_effects))
        for child in scope.required_scopes:
            result.update(member_obligations(child, visited))
        return result

    scope_edges = {}
    for scope in scopes.values():
        if set(scope.outputs) != set(scope.output_contracts):
            raise ValueError('plan.scope_output_contracts')
        dependencies(scope.outputs)
        dependencies(scope.condition)
        if scope.parent_id is not None and scope.parent_id not in all_scopes and scope.parent_id not in ports:
            raise ValueError('plan.unknown_parent_scope')
        if set(scope.required_tasks) - ports.keys():
            raise ValueError('plan.unknown_required_task')
        if set(scope.required_scopes) - all_scopes.keys():
            raise ValueError('plan.unknown_required_scope')
        for name in (*scope.required_checks, *scope.required_effects,
                     *scope.acceptance.required_checks, *scope.acceptance.required_effects):
            obligation(scope, name)
        scope_edges[scope.scope_id] = set(scope.required_scopes) & scopes.keys()
    _acyclic(scope_edges, 'plan.scope_cycle')
    _acyclic({name: {scope.parent_id} & scopes.keys() for name, scope in scopes.items()}, 'plan.scope_parent_cycle')
    dependencies(plan.outputs)

    checked, edges = [], {}
    for task in plan.tasks:
        # A task may name a cancellation namespace without declaring an
        # acceptance scope. Guards always require an explicit PreparedScope.
        if not isinstance(task.scope_id, str):
            raise ValueError('plan.invalid_task_scope')
        deps = set(task.deps)
        if deps - ports.keys():
            raise ValueError('plan.unknown_dependency')
        for name in ('inputs', 'items', 'initial', 'selector', 'forwarded', 'condition'):
            deps.update(dependencies(getattr(task, name, None)))
        if hasattr(task, 'command'):
            deps.update(dependencies(task.command.parameters))
            claims = {**dict(task.command.resources), 'worker': 1}
            if any(type(amount) is not int or amount < 0 for amount in claims.values()):
                raise ValueError('resource.invalid_claim')
            if capacities is not None:
                for resource, amount in claims.items():
                    if amount > capacities.get(resource, 1):
                        raise ValueError('resource.impossible_claim:' + resource)
            if set(task.inputs) - task.command.inputs.keys():
                raise ValueError('plan.unknown_input')
        for guard in task.guards:
            deps.update(guarded(guard))
        for guard in task.input_guards:
            deps.update(dependencies(guard.value))
        for guards in getattr(task, 'item_guards', {}).values():
            for guard in guards:
                deps.update(guarded(guard))
                deps.update(member_obligations(guard.scope_id))
        changes = {}
        nested = []
        if getattr(task, 'template', None) is not None:
            input_name = task.item_input if task.kind == 'map' else task.state_input
            nested.append(('template', task.template, input_name))
        nested.extend((key, branch, task.input_name) for key, branch in getattr(task, 'alternatives', {}).items())
        branches = {}
        for name, template, input_name in nested:
            # Captures become explicit dependencies of the enclosing control
            # task; nested execution cannot discover an unrepresented ancestor.
            validated = validate_plan(template, external_ports=ports, external_scopes=all_scopes,
                template_inputs=(*allowed_inputs, input_name), capacities=capacities,
                max_depth=max_depth, _depth=_depth + 1)
            local = {child.task_id for child in validated.tasks}
            for child in validated.tasks:
                deps.update(set(child.deps) - local)
            deps.update(dependencies(template.outputs) - local if not local else ())
            if name == 'template':
                changes['template'] = validated
            else:
                branches[name] = validated
        if branches:
            from types import MappingProxyType
            changes['alternatives'] = MappingProxyType(branches)
        edges[task.task_id] = deps & tasks.keys()
        checked.append(_record(task, deps=tuple(sorted(deps)), **changes))
    _acyclic(edges, 'plan.cycle')
    return _record(plan, tasks=tuple(checked))
