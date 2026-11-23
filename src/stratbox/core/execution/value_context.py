"""Relational source context from explicit, edition-exact owner adapters."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from functools import lru_cache
from importlib import import_module
import json
from typing import Any, get_args, get_type_hints

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot, TableSchema, TypedTable
from stratbox.shared.data.source_context import (
    SourceCoordinate, SourceUse, ValueContext, source_use_from,
)
from stratbox.shared.identity import ByteIdentity

_COORDINATES = {"source": "source_id", "family": "family_id", "source_group": "source_group_id",
    "issue": "issue_id", "asset": "asset_id", "material": "material_identity",
    "layout_edition": "layout_edition", "semantic_profile_edition": "semantic_profile_edition"}
_RULE_FIELDS = {*_COORDINATES, "at", "role", "qualification", "evidence"}


def _contract(value):
    if not isinstance(value, dict) or set(value) != {"schema_id", "version", "role"}:
        raise ValueError("registry.value_context_contract_invalid")
    return DataContract(value["schema_id"], value["version"],
        DataRole(value["role"]) if value["role"] is not None else None)


def _selector_valid(value):
    if isinstance(value, str):
        return bool(value) and all(value.split("."))
    if isinstance(value, dict):
        if set(value) == {"root"}:
            return _selector_valid(value["root"])
        if set(value) == {"literal"}:
            return isinstance(value["literal"], (str, int)) and not isinstance(value["literal"], bool)
        if set(value) == {"sha256", "size"}:
            return all(_selector_valid(item) for item in value.values())
        if set(value) == {"path", "lookup"}:
            return (_selector_valid(value["path"]) and isinstance(value["lookup"], dict)
                    and all(isinstance(key, str) and isinstance(member, str) and member
                            for key, member in value["lookup"].items()))
        if set(value) == {"join", "separator"}:
            return (isinstance(value["join"], list) and bool(value["join"])
                    and all(_selector_valid(member) for member in value["join"])
                    and isinstance(value["separator"], str) and len(value["separator"]) <= 32)
    return False


def _validate_specification(specification):
    if (not isinstance(specification, dict) or not set(specification) <= {"uses", "traverse", "context", "requirements_ref"}
            or "traverse" in specification and type(specification["traverse"]) is not bool
            or "context" in specification and not _selector_valid(specification["context"])
            or "requirements_ref" in specification and (
                not isinstance(specification["requirements_ref"], str) or not specification["requirements_ref"])):
        raise ValueError("registry.value_context_invalid")
    rules = specification.get("uses", [])
    if not isinstance(rules, list):
        raise ValueError("registry.value_context_invalid")
    for rule in rules:
        if (not isinstance(rule, dict) or not set(rule) <= _RULE_FIELDS
                or any(not _selector_valid(selector) for selector in rule.values())
                or "at" in rule and not isinstance(rule["at"], str)):
            raise ValueError("registry.value_context_invalid")


def validate_value_contexts(declarations):
    """Validate one owner's adapter syntax without importing its handlers."""
    if not isinstance(declarations, dict) or not set(declarations) <= {"types", "tables"}:
        raise ValueError("registry.value_context_invalid")
    types = declarations.get("types", {})
    tables = declarations.get("tables", [])
    if (not isinstance(types, dict) or any(not isinstance(name, str) or not name for name in types)
            or not isinstance(tables, list)):
        raise ValueError("registry.value_context_invalid")
    for specification in types.values():
        _validate_specification(specification)
    contracts = set()
    for table in tables:
        if (not isinstance(table, dict) or not {"contract", "schema_ref"} <= set(table)
                or not set(table) <= {"contract", "schema_ref", "uses", "context", "requirements_ref", "applies_to"}
                or not isinstance(table["schema_ref"], str) or table["schema_ref"].count(":") != 1):
            raise ValueError("registry.value_context_table_invalid")
        contract = _contract(table["contract"])
        if contract in contracts:
            raise ValueError("registry.value_context_duplicate")
        contracts.add(contract)
        applications = table.get("applies_to", [])
        if not isinstance(applications, list):
            raise ValueError("registry.value_context_application_invalid")
        for application in applications:
            if (not isinstance(application, dict) or set(application) != {"component", "contract"}
                    or not isinstance(application["component"], str) or not application["component"]):
                raise ValueError("registry.value_context_application_invalid")
            _contract(application["contract"])
        _validate_specification({key: value for key, value in table.items() if key in {"uses", "context", "requirements_ref"}})


@lru_cache(maxsize=1)
def _adapters():
    from stratbox.core.registry.resources import owner_directories, read_document
    result = {"types": {}, "tables": {}}
    for _, directory in owner_directories():
        declarations = read_document(directory.joinpath("OWNER.yaml")).get("value_contexts", {})
        validate_value_contexts(declarations)
        for name, specification in declarations.get("types", {}).items():
            if name in result["types"]:
                raise ValueError("registry.value_context_duplicate")
            result["types"][name] = specification
        for specification in declarations.get("tables", []):
            contract = _contract(specification["contract"])
            if contract in result["tables"]:
                raise ValueError("registry.value_context_duplicate")
            result["tables"][contract] = specification
    return result


@lru_cache(maxsize=1)
def _source_facts():
    from stratbox.core.registry.resources import resource_owners, iter_resources, read_document
    result = {}
    for owner in resource_owners():
        for resource in iter_resources(owner, "sources"):
            source = read_document(resource)
            groups = source.get("source_groups", ())
            result[source["series_id"]] = (source["family_id"],
                groups[0]["group_id"] if len(groups) == 1 else None)
    return result


@lru_cache(maxsize=1)
def _contract_sources():
    from stratbox.core.registry.resources import resource_owners, iter_resources, read_document
    bindings = {}
    for owner in resource_owners():
        for resource in iter_resources(owner, "sources"):
            source = read_document(resource)
            for group in source.get("source_groups", ()):
                for declared in group.get("contracts", ()):
                    contract = _contract({"role": None, **declared})
                    bindings.setdefault(contract, set()).add((source["series_id"], source["family_id"], group["group_id"]))
    return {contract: next(iter(values)) for contract, values in bindings.items() if len(values) == 1}


def _enrich(use):
    coordinate = use.coordinate
    facts = _source_facts().get(coordinate.source_id)
    if facts is None:
        return use
    family, source_group = facts
    return replace(use, coordinate=replace(coordinate,
        family_id=coordinate.family_id if coordinate.family_id is not None else family,
        source_group_id=coordinate.source_group_id if coordinate.source_group_id is not None else source_group))


def _select(value, segments):
    if value is None:
        return ()
    if not segments:
        return (value,)
    segment, *tail = segments
    if segment == "*":
        if not isinstance(value, (tuple, list)):
            raise ValueError("source.context_path_invalid")
        return tuple(item for member in value for item in _select(member, tail))
    if segment == "$json":
        if not isinstance(value, str):
            raise ValueError("source.context_encoding_invalid")
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            raise ValueError("source.context_encoding_invalid") from None
        return _select(decoded, tail)
    if segment == "$scalar":
        from stratbox.core.formats.dataframes import scalar_from_value
        try:
            return _select(scalar_from_value(value), tail)
        except (TypeError, ValueError):
            raise ValueError("source.context_encoding_invalid") from None
    if segment.startswith("@"):
        if isinstance(value, (tuple, list)) and all(isinstance(pair, (tuple, list)) and len(pair) == 2 for pair in value):
            value = dict(value)
        if not isinstance(value, Mapping):
            raise ValueError("source.context_path_invalid")
        return _select(value.get(segment[1:]), tail)
    if isinstance(value, Mapping):
        if segment not in value:
            raise ValueError("source.context_path_invalid")
        return _select(value[segment], tail)
    if is_dataclass(value) and not isinstance(value, type) and segment in {item.name for item in fields(value)}:
        return _select(getattr(value, segment), tail)
    raise ValueError("source.context_path_invalid")


def _read_selector(item, selector, root):
    if isinstance(selector, dict):
        if "literal" in selector:
            return selector["literal"]
        if "root" in selector:
            return _read_selector(root, selector["root"], root)
        if "lookup" in selector:
            key = _text(_read_selector(item, selector["path"], root))
            if key is None:
                return None
            try:
                return selector["lookup"][key]
            except KeyError:
                raise ValueError("source.context_lookup_unqualified") from None
        if "join" in selector:
            members = tuple(_text(_read_selector(item, member, root)) for member in selector["join"])
            return None if any(member is None for member in members) else selector["separator"].join(members)
        sha256 = _read_selector(item, selector["sha256"], root)
        size = _read_selector(item, selector["size"], root)
        return None if sha256 is None and size is None else ByteIdentity(sha256, size)
    selected = _select(item, selector.split("."))
    if len(selected) > 1:
        raise ValueError("source.context_relation_ambiguous")
    return selected[0] if selected else None


def _text(value):
    if value is None or value == "":
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value)
    raise ValueError("source.context_value_invalid")


def value_context(value, contract=None) -> ValueContext:
    """Preserve coordinates and roles; filenames and lineage remain separate.

    Each repeated anchor produces its own source use. Independent source,
    issue, group and edition sets never participate in source admission.
    Table adapters match the complete DataContract, including its data edition.
    """
    adapters = _adapters()
    uses = []

    def apply(item, specification, root, path, inherited):
        inherited = dict(inherited)
        if "context" in specification:
            selector = specification["context"]
            if isinstance(selector, str):
                selected = _select(item, selector.split("."))
                context = selected[0] if len(selected) == 1 and isinstance(selected[0], (tuple, list)) else selected
            else:
                context = _read_selector(item, selector, root)
            if context is not None:
                if not isinstance(context, (tuple, list)):
                    raise ValueError("source.context_value_invalid")
                for use in context:
                    use = source_use_from(use) if isinstance(use, dict) else use
                    if not isinstance(use, SourceUse):
                        raise ValueError("source.context_value_invalid")
                    uses.append(_enrich(use))
                if context:
                    return inherited, True
        for rule in specification.get("uses", ()):
            anchors = _select(item, rule["at"].split(".")) if "at" in rule else (item,)
            for ordinal, anchor in enumerate(anchors):
                values = dict(inherited)
                for role, field in _COORDINATES.items():
                    if role in rule:
                        selected = _read_selector(anchor, rule[role], root)
                        values[field] = selected if role == "material" else _text(selected)
                if values.get("source_id") is not None or values.get("family_id") is not None:
                    coordinate = SourceCoordinate(**values)
                    use = SourceUse(coordinate,
                        _text(_read_selector(anchor, rule["role"], root)) if "role" in rule else
                            (f"{path}.{ordinal}" if "at" in rule else path),
                        _text(_read_selector(anchor, rule["qualification"], root)) if "qualification" in rule else "declared",
                        _text(_read_selector(anchor, rule["evidence"], root)) if "evidence" in rule else None)
                    uses.append(_enrich(use))
                elif len(anchors) == 1:
                    inherited.update({key: member for key, member in values.items() if member is not None})
        return inherited, False

    def visit(item, depth=0, path="source", inherited=None, ancestors=frozenset()):
        if depth > 32:
            raise ValueError("source.input_structure_invalid")
        if not isinstance(item, (tuple, list, Mapping, DatasetSnapshot, TypedTable, SourceUse)) and (
                isinstance(item, type) or not is_dataclass(item)):
            return
        if id(item) in ancestors:
            return
        ancestors = ancestors | {id(item)}
        inherited = {} if inherited is None else inherited
        if isinstance(item, SourceUse):
            uses.append(_enrich(item))
        elif isinstance(item, TypedTable):
            specification = adapters["tables"].get(item.schema.contract)
            if specification is not None:
                if item.schema != _symbol(specification["schema_ref"]):
                    raise ValueError("source.context_schema_mismatch")
                names = tuple(column.name for column in item.schema.columns)
                for ordinal, row in enumerate(item.rows):
                    data = dict(zip(names, row))
                    apply(data, specification, data, f"{path}.{ordinal}", inherited)
        elif isinstance(item, DatasetSnapshot):
            for name, table in item.tables:
                visit(table, depth + 1, name, inherited, ancestors)
        elif isinstance(item, (tuple, list)):
            for ordinal, member in enumerate(item):
                visit(member, depth + 1, f"{path}.{ordinal}", inherited, ancestors)
        elif isinstance(item, Mapping):
            for name, member in item.items():
                visit(member, depth + 1, f"{path}.{name}", inherited, ancestors)
        elif is_dataclass(item) and not isinstance(item, type):
            identifier = type(item).__module__ + "." + type(item).__qualname__
            specification = adapters["types"].get(identifier)
            if specification is not None:
                inherited, complete = apply(item, specification, item, path, inherited)
                if complete or not specification.get("traverse", False):
                    return
            if identifier.startswith("stratbox.shared.evidence."):
                return
            for field in fields(item):
                visit(getattr(item, field.name), depth + 1, f"{path}.{field.name}", inherited, ancestors)

    visit(value)
    semantic_contract = value.manifest.contract if isinstance(value, DatasetSnapshot) else contract
    declared = _contract_sources().get(semantic_contract)
    if declared is not None:
        source_id, family_id, group_id = declared
        claims = {use.coordinate.source_id for use in uses if use.coordinate.source_id is not None}
        if claims and claims != {source_id}:
            raise ValueError("source.context_contract_mismatch")
        if not claims:
            uses.append(SourceUse(SourceCoordinate(source_id, family_id, group_id,
                material_identity=value.identity if isinstance(value, DatasetSnapshot) else None),
                qualification="contract_declared",
                evidence_ref=f"{semantic_contract.schema_id}:{semantic_contract.version}"))
    return ValueContext(tuple(uses))


def _symbol(reference):
    module, separator, name = reference.partition(":")
    if not separator:
        module, _, name = reference.rpartition(".")
    return getattr(import_module(module), name)


def validate_retained_context(value):
    """Refuse an unsupported edition of an otherwise known source-metadata schema."""
    if not isinstance(value, DatasetSnapshot):
        return
    tables = _adapters()["tables"]
    identities = {contract.schema_id for contract in tables}
    for _, table in value.tables:
        if table.schema.contract.schema_id in identities and table.schema.contract not in tables:
            raise ValueError("source.context_schema_mismatch")


def retained_context_components(snapshot, *, component=None):
    """Name only loaded components with an exact declared context adapter."""
    if not isinstance(snapshot, DatasetSnapshot):
        raise ValueError("source.snapshot_required")
    tables = _adapters()["tables"]
    if component is None:
        return tuple(name for name, table in snapshot.tables if table.schema.contract in tables)
    selected = snapshot.table(component)
    result = []
    for name, table in snapshot.tables:
        specification = tables.get(table.schema.contract)
        if specification is not None and any(application["component"] == component
                and _contract(application["contract"]) == selected.schema.contract
                for application in specification.get("applies_to", ())):
            result.append(name)
    if not result and snapshot.manifest.contract in _contract_sources():
        # A canonical atomic SourceGroup contract declares the scope of every
        # component. Generic/composite contracts receive no such inference.
        return tuple(name for name, table in snapshot.tables if table.schema.contract in tables)
    return tuple(result)


def context_requirements_refs(value):
    """Follow explicit context-policy links, never source IDs observed in data."""
    adapters = _adapters()
    references = set()
    def visit(item, active=frozenset(), depth=0):
        if depth > 32:
            raise ValueError("source.input_structure_invalid")
        if id(item) in active:
            return
        active = active | {id(item)}
        if isinstance(item, DatasetSnapshot):
            for _, table in item.tables:
                specification = adapters["tables"].get(table.schema.contract, {})
                if "requirements_ref" in specification:
                    references.add(specification["requirements_ref"])
        elif isinstance(item, (tuple, list)):
            for member in item:
                visit(member, active, depth + 1)
        elif isinstance(item, Mapping):
            for member in item.values():
                visit(member, active, depth + 1)
        elif is_dataclass(item) and not isinstance(item, type):
            specification = adapters["types"].get(type(item).__module__ + "." + type(item).__qualname__)
            if specification is not None:
                if "requirements_ref" in specification:
                    references.add(specification["requirements_ref"])
                if not specification.get("traverse", False):
                    return
            for field in fields(item):
                visit(getattr(item, field.name), active, depth + 1)
    visit(value)
    return tuple(sorted(references))


def _validate_type_path(kind, path):
    segments = path.split(".")
    def walk(annotation, remaining):
        if not remaining or annotation is Any:
            return
        segment, *tail = remaining
        arguments = get_args(annotation)
        if arguments:
            if segment == "*":
                for argument in arguments:
                    if argument is not Ellipsis:
                        walk(argument, tail)
                return
            errors = []
            for argument in arguments:
                if argument is type(None):
                    continue
                try:
                    walk(argument, remaining)
                    return
                except ValueError as error:
                    errors.append(error)
            if errors:
                raise errors[0]
            return
        if segment.startswith(("@", "$")):
            return  # Dynamic mapping contents are validated against actual values.
        if not isinstance(annotation, type) or not is_dataclass(annotation):
            raise ValueError("registry.value_context_path_invalid")
        if segment not in {field.name for field in fields(annotation)}:
            raise ValueError("registry.value_context_path_invalid")
        field = next(field for field in fields(annotation) if field.name == segment)
        # Resolve only the selected field. Optional dataframe annotations in an
        # unrelated field must not force a scientific import for source paths.
        scope = type("ContextField", (), {"__annotations__": {segment: field.type}})
        hints = get_type_hints(scope, vars(import_module(annotation.__module__)),
                               {annotation.__name__: annotation})
        walk(hints.get(segment, Any), tail)
    walk(kind, segments)


def validate_value_context_links(catalog=None):
    """Static/fixture validation of type paths and exact metadata schemas.

    Delivery checks call this explicitly. Ordinary metadata discovery does not
    import domain handlers or optional scientific engines to perform this check.
    Every actual use also validates its selected fields before execution.
    """
    adapters = _adapters()
    references = {specification["requirements_ref"] for collection in adapters.values()
                  for specification in collection.values() if "requirements_ref" in specification}
    if references:
        if catalog is None:
            from stratbox.core.registry import operation_catalog
            catalog = operation_catalog()
        for reference in references:
            if not catalog.document(reference).get("source_requirements"):
                raise ValueError("registry.value_context_requirements_unknown")
    def selector_paths(selector, anchor=None):
        if isinstance(selector, str):
            yield f"{anchor}.{selector}" if anchor else selector
        elif "root" in selector:
            yield selector["root"]
        elif "lookup" in selector:
            yield from selector_paths(selector["path"], anchor)
        elif "join" in selector:
            for member in selector["join"]:
                yield from selector_paths(member, anchor)
        elif "sha256" in selector:
            for member in selector.values():
                yield from selector_paths(member, anchor)

    def selectors(specification):
        if "context" in specification:
            yield from selector_paths(specification["context"])
        for rule in specification.get("uses", ()):
            anchor = rule.get("at")
            if anchor:
                yield anchor
            for name, selector in rule.items():
                if name != "at":
                    yield from selector_paths(selector, anchor)
    for identifier, specification in adapters["types"].items():
        try:
            kind = _symbol(identifier)
            if not isinstance(kind, type) or not is_dataclass(kind):
                raise ValueError("registry.value_context_type_invalid")
            for path in selectors(specification):
                if isinstance(path, dict):
                    path = path["root"]
                _validate_type_path(kind, path)
        except (ImportError, AttributeError, NameError, TypeError) as error:
            raise ValueError(f"registry.value_context_type_invalid:{identifier}") from error
    for contract, specification in adapters["tables"].items():
        schema = _symbol(specification["schema_ref"])
        if not isinstance(schema, TableSchema) or schema.contract != contract:
            raise ValueError("registry.value_context_schema_mismatch")
        columns = {column.name for column in schema.columns}
        for path in selectors(specification):
            if not isinstance(path, str) or path.split(".")[0] not in columns:
                raise ValueError("registry.value_context_column_invalid")
