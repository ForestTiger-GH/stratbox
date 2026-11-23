"""Exhaustive computational projection of typed operation requests."""

from __future__ import annotations

from collections.abc import Mapping
from stratbox.core.execution.values import argument_identity, argument_value, plain
from stratbox.core.execution.value_context import value_context
from stratbox.shared.data.source_context import ValueContext
from stratbox.shared.identity import canonical_manifest_bytes

_COMPUTATIONAL = frozenset({"input", "parameter", "method", "dependency"})
_OMITTED = object()


def _select(value, path):
    for part in path.split(".") if path else ():
        value = value[part] if isinstance(value, Mapping) else getattr(value, part)
    return value


def source_context_value(*contexts):
    """Commit linked semantic coordinates without proof/delivery chronology."""
    uses = {}
    for context in contexts:
        if context is None:
            continue
        if not isinstance(context, ValueContext):
            raise ValueError("source.context_invalid")
        for use in context.uses:
            value = {"coordinate": argument_value(use.coordinate), "input_role": use.input_role}
            uses[canonical_manifest_bytes(value)] = value
    return {"uses": [uses[key] for key in sorted(uses)]}


def filter_parameters(definition, parameters):
    """Remove technical request coordinates from handler-supplied metadata too."""
    declared = tuple(getattr(definition, "request_fields", ()))
    values = argument_value(parameters or {})
    if not isinstance(values, dict):
        raise ValueError("processing.parameters_invalid")
    roles = {field.path: field.role for field in declared}
    result = {}
    for name, value in values.items():
        role = roles.get(name)
        if role is None:
            parent = next((path for path in roles if path == "" or name.startswith(path + ".")), None)
            role = roles.get(parent)
        if role is not None and role not in _COMPUTATIONAL:
            continue
        descendants = [field for field in declared if field.path.startswith(name + ".")]
        if descendants:
            selected = {}
            for field in descendants:
                if field.role not in _COMPUTATIONAL:
                    continue
                relative = field.path[len(name) + 1:]
                try:
                    selected[relative] = _select(value, relative)
                except (AttributeError, KeyError, TypeError):
                    continue
            if selected:
                result[name] = selected
        else:
            result[name] = value
    return result


def capture_arguments(definition, request, *, checkpoint=None, budget=None, cache=None,
                      source_contexts=None):
    """Capture every computational field, excluding explicitly technical roles.

    Canonical operations provide an exhaustive request policy. Direct extension
    definitions without one conservatively commit the complete request, making
    a missing declaration visible without silently omitting meaningful fields.
    """
    if checkpoint is not None:
        checkpoint()
    policies = tuple(getattr(definition, "request_fields", ()))
    roles = {item.path: item.role for item in policies}
    semantics = definition.processing
    arguments, parameters, covered = {}, {}, set()

    def projected(path):
        if path in roles:
            return _select(request, path) if roles[path] in _COMPUTATIONAL else _OMITTED
        descendants = [item for item in policies if not path or item.path.startswith(path + ".")]
        if descendants:
            return {item.path[len(path) + 1:] if path else item.path: _select(request, item.path)
                    for item in descendants if item.role in _COMPUTATIONAL}
        if policies:
            parent = next((name for name in roles if path.startswith(name + ".") or name == ""), None)
            if parent is not None and roles[parent] not in _COMPUTATIONAL:
                return _OMITTED
        return _select(request, path)

    def identity(value):
        return plain(argument_identity(value, checkpoint=checkpoint, budget=budget, cache=cache))

    if semantics is not None:
        for port in semantics.inputs:
            value = projected(port.path)
            if value is _OMITTED:
                continue
            digest = identity(value)
            context_key = ("source_context", id(value), port.contract, port.alternatives)
            retained = None if cache is None else cache.get(context_key)
            if retained is not None and retained[0] is value:
                intrinsic, actual_contract = retained[1:]
            else:
                for actual_contract in (port.contract, *port.alternatives):
                    try:
                        intrinsic = value_context(value, actual_contract)
                        break
                    except ValueError as error:
                        if str(error) != "source.context_contract_mismatch" or actual_contract == (
                                port.alternatives[-1] if port.alternatives else port.contract):
                            raise
                if cache is not None and ("argument", id(value)) in cache:
                    cache[context_key] = (value, intrinsic, actual_contract)
            supplied = None if source_contexts is None else source_contexts.get(port.name)
            arguments[port.name] = {"contract": plain(actual_contract), "identity": digest,
                                    "context": source_context_value(intrinsic, supplied)}
            covered.add(port.path)
        for name in semantics.parameters:
            value = projected(name)
            if value is not _OMITTED:
                parameters[name] = argument_value(value)
                covered.add(name)
    for field in policies:
        if field.role not in _COMPUTATIONAL or field.path in covered:
            continue
        if any(path == "" or field.path.startswith(path + ".") for path in covered):
            continue
        value = _select(request, field.path)
        if field.role in {"parameter", "method"}:
            parameters[field.path] = argument_value(value)
        else:
            arguments["field:" + (field.path or "request")] = {"role": field.role, "identity": identity(value)}
    if not policies:
        # The fallback complements named ports, including fields absent from
        # processing.parameters. No arbitrary field spelling implies exclusion.
        arguments["request"] = {"identity": identity(request)}
    return arguments, parameters
