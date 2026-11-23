"""Typed path and request-coverage admission without executing domain work."""
from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from collections.abc import Sequence, Set, Iterable
import sys
import types
import typing

from stratbox.shared.data.operations import COMPUTATIONAL_FIELD_ROLES


def _annotation(owner, value):
    if not isinstance(value, str):
        return value
    namespace = {**vars(typing), **vars(sys.modules[owner.__module__])}
    try:
        return eval(value, namespace)
    except (NameError, TypeError, AttributeError):
        return value


def _choices(kind):
    origin = typing.get_origin(kind)
    if origin in (typing.Union, types.UnionType):
        return tuple(item for choice in typing.get_args(kind) if choice is not type(None) for item in _choices(choice))
    if origin is typing.Annotated:
        return _choices(typing.get_args(kind)[0])
    return (kind,)


def resolve_type_path(kind, path, *, init_only=False):
    """Resolve dataclass/property coordinates, preserving union alternatives."""
    if not path:
        return kind
    choices = _choices(kind)
    for segment in path.split("."):
        following = []
        for choice in choices:
            if is_dataclass(choice):
                match = next((item for item in fields(choice) if item.name == segment and (item.init or not init_only)), None)
                if match is not None:
                    following.extend(_choices(_annotation(choice, match.type)))
                    continue
            attribute = getattr(choice, segment, None) if isinstance(choice, type) else None
            if not init_only and isinstance(attribute, property):
                following.extend(_choices(_annotation(choice, attribute.fget.__annotations__.get("return", object))))
        if not following:
            raise ValueError("registry.type_path_unavailable:" + path)
        choices = tuple(following)
    return choices[0] if len(choices) == 1 else tuple(choices)


def is_collection_type(kind):
    return any((typing.get_origin(choice) or choice) in {tuple, list, set, frozenset, Sequence, Set, Iterable}
               for choice in _choices(kind))


def validate_request_contract(definition, *, require_classification=False):
    """Every initialized request coordinate is classified before trusted use."""
    policies = {item.path: item for item in definition.request_fields}
    if require_classification or policies:
        for path in policies:
            resolve_type_path(definition.request_type, path, init_only=True)
        def cover(kind, prefix="", depth=0):
            if prefix in policies:
                return
            if depth > 64:
                raise ValueError("registry.request_schema_recursive:" + prefix)
            alternatives = _choices(kind)
            for choice in alternatives:
                if not is_dataclass(choice):
                    if prefix or not policies:
                        raise ValueError("registry.request_field_unclassified:" + prefix)
                    continue
                for item in fields(choice):
                    if not item.init:
                        continue
                    path = prefix + "." + item.name if prefix else item.name
                    if path in policies:
                        continue
                    if not any(candidate.startswith(path + ".") for candidate in policies):
                        raise ValueError("registry.request_field_unclassified:" + path)
                    cover(_annotation(choice, item.type), path, depth + 1)
        cover(definition.request_type)
    processing = definition.processing
    if processing is None:
        return
    for port in processing.inputs:
        field_type = resolve_type_path(definition.request_type, port.path, init_only=True)
        if require_classification and port.collection != is_collection_type(field_type):
            raise ValueError("registry.input_collection_mismatch:" + port.name)
        if policies:
            applicable = [item for path, item in policies.items()
                          if not port.path or not path or path == port.path
                          or path.startswith(port.path + ".") or port.path.startswith(path + ".")]
            if not applicable or not any(item.role in COMPUTATIONAL_FIELD_ROLES for item in applicable):
                raise ValueError("registry.input_not_computational:" + port.name)
    for name in processing.parameters:
        resolve_type_path(definition.request_type, name, init_only=True)
    if require_classification and is_dataclass(definition.request_type):
        required = {item.name for item in fields(definition.request_type) if item.init and item.name in processing.parameters
                    and item.default is MISSING and item.default_factory is MISSING}
        if required != set(processing.required_parameters):
            raise ValueError("registry.required_parameters_mismatch")
    result_types = definition.value_type if isinstance(definition.value_type, tuple) else (definition.value_type,)
    for port in processing.outputs:
        if port.source_context_path is not None:
            errors = []
            for kind in result_types:
                try:
                    resolve_type_path(kind, port.source_context_path)
                    break
                except ValueError as error:
                    errors.append(error)
            else:
                raise ValueError("registry.output_context_path_unavailable:" + port.name)
        for kind in result_types:
            try:
                output_type = resolve_type_path(kind, port.path)
                if require_classification and port.collection != is_collection_type(output_type):
                    raise ValueError("registry.output_collection_mismatch:" + port.name)
                break
            except ValueError as error:
                if str(error).startswith("registry.output_collection_mismatch"):
                    raise
                continue
        else:
            raise ValueError("registry.output_path_unavailable:" + port.name)
