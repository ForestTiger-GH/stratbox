"""Isolate bound plan materials without charging immutable graph metadata."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from types import MappingProxyType
from uuid import uuid4

from .ownership import _immutable, isolate_value


def _sealed(value):
    return _immutable(value) or (isinstance(value, MappingProxyType)
        and all(_sealed(item) for item in value.values()))


def _material_size(value, seen, *, named=False):
    from stratbox.core.execution.retention import retained_size
    from .placement import ManagedResult, ManagedProjection, ManagedCollection
    if _sealed(value) or isinstance(value, (ManagedResult, ManagedProjection, ManagedCollection)) or id(value) in seen:
        return 0
    seen.add(id(value))
    if isinstance(value, Mapping):
        return (0 if named else len(value) * 16) + sum(_material_size(item, seen) for item in value.values())
    if isinstance(value, (tuple, list)):
        return len(value) * 8 + sum(_material_size(item, seen) for item in value)
    if is_dataclass(value) and not isinstance(value, type):
        return sum(_material_size(getattr(value, member.name), seen) for member in fields(value) if member.init)
    return retained_size(value)


def _copy_material(value, memo):
    from .placement import ManagedResult, ManagedProjection, ManagedCollection
    if _sealed(value) or isinstance(value, (ManagedResult, ManagedProjection, ManagedCollection)):
        return value
    if id(value) in memo:
        return memo[id(value)]
    if isinstance(value, Mapping):
        copied = {}
        memo[id(value)] = copied
        copied.update((key, _copy_material(item, memo)) for key, item in value.items())
    elif isinstance(value, list):
        copied = []
        memo[id(value)] = copied
        copied.extend(_copy_material(item, memo) for item in value)
    elif isinstance(value, tuple):
        copied = tuple(_copy_material(item, memo) for item in value)
    elif is_dataclass(value) and not isinstance(value, type):
        copied = replace(value, **{member.name: _copy_material(getattr(value, member.name), memo)
                                  for member in fields(value) if member.init})
    else:
        copied = isolate_value(value)
    memo[id(value)] = copied
    return copied


def _rewrite(record, material):
    """Visit the material-bearing fields of compiled and dynamic graph nodes."""
    if not is_dataclass(record) or isinstance(record, type):
        return record
    names = {member.name for member in fields(record) if member.init}
    changes = {}
    if {"tasks", "scopes", "outputs"} <= names:
        changes["tasks"] = tuple(_rewrite(task, material) for task in record.tasks)
        changes["scopes"] = tuple(_rewrite(scope, material) for scope in record.scopes)
        changes["outputs"] = material(record.outputs, True)
    elif "task_id" in names:
        for name in ("inputs", "parameters"):
            changes[name] = material(getattr(record, name), True)
        for name in ("map", "collect", "condition"):
            if getattr(record, name, None) is not None:
                changes[name] = _rewrite(getattr(record, name), material)
        if "conditions" in names:
            changes["conditions"] = tuple(_rewrite(value, material) for value in record.conditions)
    elif "scope_id" in names and "outputs" in names:
        changes["outputs"] = material(record.outputs, True)
        if "conditions" in names:
            changes["conditions"] = tuple(_rewrite(value, material) for value in record.conditions)
    elif "items" in names and "body" in names:
        changes["items"] = material(record.items, False)
        changes["inputs"] = material(record.inputs, True)
        changes["body"] = _rewrite(record.body, material)
    elif "selection" in names and "capability_id" in names:
        changes["selection"] = material(record.selection, True)
    elif "steps" in names or "scenarios" in names:
        name = "steps" if "steps" in names else "scenarios"
        changes[name] = tuple(_rewrite(value, material) for value in getattr(record, name))
        changes["outputs"] = material(record.outputs, True)
    elif "scenario" in names:
        changes["scenario"] = _rewrite(record.scenario, material)
        changes["inputs"] = material(record.inputs, True)
    elif "operation_id" in names and "parameters" in names:
        changes["inputs"] = material(record.inputs, True)
        changes["parameters"] = material(record.parameters, True)
        if getattr(record, "condition", None) is not None:
            changes["condition"] = _rewrite(record.condition, material)
    elif "collect" in names:
        changes["collect"] = _rewrite(record.collect, material)
    elif {"contract", "element_contract", "inputs"} <= names:
        changes["inputs"] = material(record.inputs, False)
    elif "equals" in names:
        changes["equals"] = material(record.equals, False)
    return record if all(value is getattr(record, name) for name, value in changes.items()) else replace(record, **changes)


def isolate_plan(plan, ledger):
    """Own mutable input/parameter/map materials for the retained plan's life.

    Shared bound objects get one copied allocation and one reservation. Graph
    identities, resource declarations, output contracts and catalog projections
    stay metadata rather than becoming fictitious retained payload bytes.
    """
    from .placement import _read_scope, _CapacityLease
    scope = _read_scope.get()
    if scope is None:
        raise ValueError("value.read_scope_required")
    if scope._closed:
        raise ValueError("value.read_scope_closed")
    seen = set()
    size = 0

    def measure(value, named):
        nonlocal size
        size += _material_size(value, seen, named=named)
        return value

    _rewrite(plan, measure)
    owner = "plan-inputs:" + uuid4().hex
    if ledger is not None and size:
        try:
            reserved = ledger.reserve(owner, {"retained_bytes": size})
        except ValueError as error:
            if str(error) != "resource.unsatisfiable":
                raise
            reserved = False
        if not reserved:
            raise ValueError("resource.retained_bytes")
    try:
        memo = {}
        copied = _rewrite(plan, lambda value, named: _copy_material(value, memo))
    except BaseException:
        if ledger is not None and size:
            ledger.release(owner)
        raise
    if size:
        scope.own(_CapacityLease(ledger, owner))
    return copied
