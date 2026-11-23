"""Staged admission of one immutable registry graph.

Metadata, real Python links and executable handlers are separate proofs. No
level runs a domain algorithm or claims the success of semantic fixtures.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
from functools import lru_cache
import inspect
import json
import types
import typing

from stratbox.shared.identity import ByteIdentity
from stratbox.core.registry.catalog import RegistryError
from stratbox.core.registry.resources import (
    iter_resources, owner_directories, read_document, resource_inventory, installed_resource_inventory,
)

_LEVELS = ("metadata", "typed", "executable")
_KINDS = ("sources", "operations", "profiles", "routes", "families", "groups")


@dataclass(frozen=True, slots=True)
class AdmissionCheck:
    responsibility: str
    state: str
    count: int = 0


@dataclass(frozen=True, slots=True)
class CatalogAdmission:
    level: str
    owners: tuple[str, ...]
    operation_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    profile_ids: tuple[str, ...]
    source_resource_identity: ByteIdentity
    semantic_registry_identity: ByteIdentity
    installed_distribution_identity: ByteIdentity
    implementation_identity: ByteIdentity | None
    checks: tuple[AdmissionCheck, ...]

    @property
    def admitted(self):
        return True


def _plain(value):
    if isinstance(value, type):
        return value.__module__ + ":" + value.__qualname__
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_plain(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def _identity(value):
    return ByteIdentity.of(json.dumps(_plain(value), sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode("utf-8"))


@lru_cache(maxsize=1)
def _canonical_links():
    from stratbox.core.registry.catalog import OperationCatalog
    from stratbox.core.registry.operations import owner_ids, owner_registration
    return OperationCatalog.from_registrations(*(owner_registration(owner) for owner in owner_ids()))


def _link_catalog(catalog):
    """Cross-owner references resolve in the complete canonical graph."""
    if not catalog.registrations or any(ref.definition is not None for ref in catalog.references):
        return catalog
    known = _canonical_links()
    if not {item.owner_id for item in catalog.registrations} <= {item.owner_id for item in known.registrations}:
        return catalog
    return known


def _records():
    result = []
    for owner, directory in owner_directories():
        manifest = read_document(directory.joinpath("OWNER.yaml"))
        if manifest.get("owner_id") != owner:
            raise RegistryError("registry.owner_mismatch")
        result.append(manifest)
        for kind in _KINDS:
            for path in iter_resources(owner, kind):
                document = read_document(path)
                if document.get("owner_id") != owner:
                    raise RegistryError("registry.owner_mismatch")
                result.append(document)
    return tuple(result)


def _normalized_record(value):
    if value.get("schema") != "stratbox.operation":
        return value
    from stratbox.core.registry.operations import metadata_definition
    result = dict(value)
    definition = _plain(metadata_definition(value["definition"]["operation_id"]))
    definition["request_type"] = value["definition"]["request_type"]
    definition["value_type"] = value["definition"]["value_type"]
    result["definition"] = definition
    return result


def _context_requirement_links(records):
    """Resolve context role owners once; this link never expands other adapters."""
    from stratbox.shared.identifiers import safe_token
    operations = {record["definition"]["operation_id"]: record for record in records
                  if record.get("schema") == "stratbox.operation"}
    count = 0
    for owner in records:
        if "value_contexts" not in owner:
            continue
        declarations = owner["value_contexts"]
        specifications = (*declarations.get("types", {}).values(), *declarations.get("tables", []))
        for specification in specifications:
            if "requirements_ref" not in specification:
                continue
            reference = specification["requirements_ref"]
            try:
                safe_token(reference)
            except (TypeError, ValueError) as error:
                raise RegistryError("registry.value_context_requirements_invalid") from error
            target = operations.get(reference)
            if target is None:
                raise RegistryError("registry.value_context_requirements_unknown:" + reference)
            if target["owner_id"] != owner["owner_id"]:
                raise RegistryError("registry.value_context_requirements_owner_mismatch:" + reference)
            if not target.get("source_requirements"):
                raise RegistryError("registry.value_context_requirements_empty:" + reference)
            count += 1
    return count


def _profile_metadata(owners):
    from stratbox.core.registry.operations import _reference
    count = 0
    for owner in owners:
        for path in iter_resources(owner, "profiles"):
            declaration = read_document(path).get("declaration", {})
            for field in ("implementation_ref", "admission_ref"):
                if field in declaration:
                    _reference(declaration[field], owner=owner)
                    count += 1
            if "implementation_parameters" in declaration:
                parameters = declaration["implementation_parameters"]
                if not isinstance(parameters, dict) or any(not isinstance(key, str) for key in parameters) or "implementation_ref" not in declaration:
                    raise RegistryError("registry.profile_parameters_invalid")
    return count


def _profile_links(owners):
    from stratbox.core.registry.operations import _reference
    from stratbox.core.registry.catalog import _load
    count = 0
    for owner in owners:
        for path in iter_resources(owner, "profiles"):
            declaration = read_document(path).get("declaration", {})
            for field in ("implementation_ref", "admission_ref"):
                reference = declaration.get(field)
                if reference is None:
                    continue
                _reference(reference, owner=owner)
                try:
                    linked = _load(reference)
                except (ImportError, AttributeError) as error:
                    raise RegistryError("registry.profile_reference_unavailable:" + reference) from error
                if field == "admission_ref" and not callable(linked):
                    raise RegistryError("registry.profile_admission_not_callable")
                if field == "implementation_ref" and "implementation_parameters" in declaration:
                    parameters = declaration["implementation_parameters"]
                    if not isinstance(parameters, dict) or not callable(linked):
                        raise RegistryError("registry.profile_parameters_invalid")
                    try:
                        inspect.signature(linked).bind_partial(**parameters)
                    except (TypeError, ValueError) as error:
                        raise RegistryError("registry.profile_parameters_invalid") from error
                count += 1
    return count


def _accepts(annotation, value):
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if annotation is typing.Any or annotation is object:
        return True
    if origin in (typing.Union, types.UnionType):
        return any(_accepts(item, value) for item in args)
    if origin is typing.Literal:
        return any(type(value) is type(item) and value == item for item in args)
    if origin in (tuple, list, set, frozenset):
        if not isinstance(value, origin):
            return False
        if origin is tuple and args and args[-1] is not Ellipsis:
            return len(args) == len(value) and all(_accepts(kind, item) for kind, item in zip(args, value))
        return not args or all(_accepts(args[0], item) for item in value)
    if annotation in (int, float, bool):
        return type(value) is annotation or annotation is float and type(value) is int
    if isinstance(annotation, type):
        return isinstance(value, annotation)
    return False


def _binding_types(catalog, owners):
    from stratbox.core.registry.sources import source_cards
    from stratbox.core.registry.type_links import resolve_type_path
    count = 0
    for owner in owners:
        for card in source_cards(owner):
            for binding in card.operations:
                if not binding.parameters:
                    continue
                definition = catalog.get(binding.operation_id)
                for name, value in binding.parameters:
                    annotation = resolve_type_path(definition.request_type, name, init_only=True)
                    if not _accepts(annotation, value):
                        raise RegistryError("registry.source_parameter_type_mismatch:" + card.series_id + ":" + binding.operation_id + ":" + name)
                    count += 1
    return count


@lru_cache(maxsize=64)
def _admit_registry_snapshot(catalog, *, level="metadata"):
    """Admit declarations, typed links, then handlers without executing work."""
    if level not in _LEVELS:
        raise RegistryError("registry.admission_level_invalid")
    from stratbox.core.registry.operations import validate_operation_document, validate_request_contract
    from stratbox.core.registry.sources import validate_source_metadata, validate_source_links
    owners = tuple(sorted(item.owner_id for item in catalog.registrations))
    records = _records()
    for document in records:
        if document.get("schema") == "stratbox.operation":
            validate_operation_document(document, owner_id=document["owner_id"])
    links = _link_catalog(catalog)
    source_count = validate_source_metadata(links)
    context_requirement_count = _context_requirement_links(records)
    _profile_metadata(tuple(owner for owner, _ in owner_directories()))
    for reference in catalog.references:
        definition = catalog.metadata(reference.operation_id)
        if reference.wire_contract_ref is not None and definition.possible_effects:
            raise RegistryError("registry.read_only_effects")
    checks = [AdmissionCheck("declaration_shapes", "admitted", len(records)),
              AdmissionCheck("metadata_links", "admitted", source_count),
              AdmissionCheck("context_requirement_links", "admitted", context_requirement_count),
              AdmissionCheck("semantic_fixtures", "not_run")]
    implementation = None
    if level in {"typed", "executable"}:
        for reference in catalog.references:
            definition = catalog.get(reference.operation_id)
            validate_request_contract(definition, require_classification=True)
        validate_source_links(links)
        profile_count = _profile_links(owners)
        parameter_count = _binding_types(links, owners)
        from stratbox.core.execution.value_context import validate_value_context_links
        validate_value_context_links(links)
        from stratbox.core.execution.methods import method_descriptor
        methods = tuple((ref.operation_id, method_descriptor(catalog.get(ref.operation_id)).identity) for ref in catalog.list_refs())
        implementation = _identity(methods)
        checks.extend((AdmissionCheck("request_types_and_fields", "admitted", len(catalog.references)),
                       AdmissionCheck("profile_python_links", "admitted", profile_count),
                       AdmissionCheck("bound_parameter_types", "admitted", parameter_count),
                       AdmissionCheck("context_type_links", "admitted"),
                       AdmissionCheck("method_dependencies", "admitted", len(methods))))
    if level == "executable":
        for reference in catalog.references:
            definition, handler, _ = catalog.resolve(reference.operation_id)
            try:
                signature = inspect.signature(handler)
                options = {"context": None}
                runtime = signature.parameters.get("runtime")
                if runtime is not None and runtime.default is runtime.empty and definition.runtime_dependencies:
                    options["runtime"] = object()
                signature.bind(object(), **options)
            except (TypeError, ValueError) as error:
                raise RegistryError("registry.handler_signature_invalid:" + reference.operation_id) from error
        checks.append(AdmissionCheck("executable_handlers", "admitted", len(catalog.references)))
    source_ids = tuple(sorted(record["series_id"] for record in records
                              if record.get("schema") == "stratbox.source" and record["owner_id"] in owners))
    profiles = tuple(sorted(record["profile_id"] for record in records
                            if record.get("schema") in {"stratbox.source-profile", "stratbox.processing-profile"}
                            and record["owner_id"] in owners))
    normalized = sorted((_normalized_record(record) for record in records),
                        key=lambda record: json.dumps(record, sort_keys=True, ensure_ascii=False))
    return CatalogAdmission(level, owners, tuple(ref.operation_id for ref in catalog.list_refs()), source_ids, profiles,
                            _identity(resource_inventory()), _identity(normalized), _identity(installed_resource_inventory()), implementation, tuple(checks))


def admit_registry_snapshot(catalog, *, level="metadata", refresh=False):
    """Reuse immutable admission, or explicitly refresh a changed development tree."""
    if type(refresh) is not bool:
        raise RegistryError("registry.admission_refresh_invalid")
    if refresh:
        return _admit_registry_snapshot.__wrapped__(catalog, level=level)
    return _admit_registry_snapshot(catalog, level=level)


validate_catalog = admit_registry_snapshot
