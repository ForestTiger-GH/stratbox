"""Explicit semantic context adapters, independent of transport provenance.

Owner declarations identify the fields and metadata columns that carry source,
group, issue and edition meaning. An arbitrary field named ``source_id`` never
becomes a source claim merely because of its spelling.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from functools import lru_cache
import json

from stratbox.shared.data.snapshots import DatasetSnapshot


@dataclass(frozen=True, slots=True)
class ValueContext:
    source_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...] = ()
    issue_ids: tuple[str, ...] = ()
    editions: tuple[str, ...] = ()


_ROLES = {"source": "source_ids", "group": "group_ids", "issue": "issue_ids", "edition": "editions"}


def validate_value_contexts(declarations):
    """Validate an owner's adapter declarations without importing its code."""
    if not isinstance(declarations, dict) or not set(declarations) <= {"types", "tables"}:
        raise ValueError("registry.value_context_invalid")
    for adapters in declarations.values():
        if not isinstance(adapters, dict):
            raise ValueError("registry.value_context_invalid")
        for identifier, specification in adapters.items():
            if (not isinstance(identifier, str) or not identifier or not isinstance(specification, dict)
                    or not set(specification) <= {*_ROLES, "traverse"}
                    or "traverse" in specification and type(specification["traverse"]) is not bool):
                raise ValueError("registry.value_context_invalid")
            for role, paths in specification.items():
                if role != "traverse" and (not isinstance(paths, list) or any(
                    not isinstance(path, str) or not path or any(not part for part in path.split("."))
                    for path in paths
                )):
                    raise ValueError("registry.value_context_invalid")


@lru_cache(maxsize=1)
def _adapters():
    from stratbox.core.registry.resources import owner_directories, read_document
    result = {"types": {}, "tables": {}}
    for _, directory in owner_directories():
        declarations = read_document(directory.joinpath("OWNER.yaml")).get("value_contexts", {})
        validate_value_contexts(declarations)
        for kind, adapters in declarations.items():
            for identifier, specification in adapters.items():
                if identifier in result[kind]:
                    raise ValueError("registry.value_context_duplicate")
                result[kind][identifier] = specification
    return result


def _select(value, segments):
    if value is None:
        return ()
    if not segments:
        return () if value is None else (value,)
    segment, *tail = segments
    if segment == "*":
        if not isinstance(value, (tuple, list)):
            return ()
        return tuple(item for member in value for item in _select(member, tail))
    if segment == "$json":
        if not isinstance(value, str):
            return ()
        try:
            return _select(json.loads(value), tail)
        except (ValueError, TypeError):
            raise ValueError("source.context_encoding_invalid") from None
    if segment.startswith("@"):
        if isinstance(value, (tuple, list)) and all(isinstance(pair, (tuple, list)) and len(pair) == 2 for pair in value):
            value = dict(value)
        if not isinstance(value, Mapping):
            return ()
        return _select(value.get(segment[1:]), tail)
    if isinstance(value, Mapping):
        if segment not in value:
            raise ValueError("source.context_path_invalid")
        return _select(value[segment], tail)
    if is_dataclass(value) and not isinstance(value, type) and segment in {item.name for item in fields(value)}:
        return _select(getattr(value, segment), tail)
    raise ValueError("source.context_path_invalid")


def value_context(value, contract=None) -> ValueContext:
    """Read only declared semantic paths; receipts and storage labels stay opaque.

    Complete and selected snapshots use the same metadata-table adapters. Their
    dataset ID, physical path, manifest inputs and producer history imply no
    logical source identity. Domain decoding retains its own schema validation.
    """
    adapters = _adapters()
    collected = {role: set() for role in _ROLES}
    seen = set()

    def apply(item, declaration):
        for role in _ROLES:
            for path in declaration.get(role, ()):
                for identity in _select(item, path.split(".")):
                    if identity is not None and identity != "":
                        if not isinstance(identity, (str, int)) or isinstance(identity, bool):
                            raise ValueError("source.context_value_invalid")
                        collected[role].add(str(identity))

    def visit(item, depth=0):
        if depth > 32:
            raise ValueError("source.input_structure_invalid")
        if id(item) in seen:
            return
        seen.add(id(item))
        if isinstance(item, DatasetSnapshot):
            for _, table in item.tables:
                declaration = adapters["tables"].get(table.schema.contract.schema_id)
                if declaration is not None:
                    names = tuple(column.name for column in table.schema.columns)
                    for row in table.rows:
                        apply(dict(zip(names, row)), declaration)
            return
        if isinstance(item, (tuple, list)):
            for member in item:
                visit(member, depth + 1)
        elif isinstance(item, Mapping):
            for member in item.values():
                visit(member, depth + 1)
        elif is_dataclass(item) and not isinstance(item, type):
            identifier = type(item).__module__ + "." + type(item).__qualname__
            declaration = adapters["types"].get(identifier)
            if declaration is not None:
                apply(item, declaration)
                if not declaration.get("traverse", False):
                    return
            # Evidence belongs to a different namespace even when its recorded
            # transport/source label happens to equal a registered series ID.
            if identifier.startswith("stratbox.shared.evidence."):
                return
            for field in fields(item):
                visit(getattr(item, field.name), depth + 1)

    visit(value)
    return ValueContext(**{name: tuple(sorted(collected[role])) for role, name in _ROLES.items()})
