"""Canonical sources, route applicability and independently owned profiles.

Stages describe processing classes. Exact port contracts decide value handoff;
source bindings retain publisher-specific applicability and qualifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextvars import ContextVar
from functools import lru_cache
import copy
from types import MappingProxyType

from stratbox.shared.identifiers import safe_token
from stratbox.shared.data.operations import ProcessingStage
from stratbox.shared.data.sources import SourceGroup
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.resources import iter_resources, read_document, resource_owners
from stratbox.domains.registry.catalog import SourceCard, SourceProfile, SourceOperation

_SOURCE_KEYS = {"schema", "owner_id", "publisher_id", "family_id", "series_id", "title", "issue_model", "formats", "processing", "family_profile", "position", "publication", "source_groups"}
_ROUTE_KEYS = {"schema", "owner_id", "profile_id", "profiles", "qualifications"}
_OPERATION_REQUIRED = {"operation_id"}
_OPERATION_OPTIONAL = {"state", "reason", "parameters", "formats", "identity_parameter", "auxiliary_sources", "context_scope"}
_PROFILE_KEYS = {"profile_id", "kind", "formats", "scope"}


def _shape(value, keys, code, *, optional=()):
    if not isinstance(value, dict) or not set(keys) <= set(value) or set(value) - set(keys) - set(optional):
        raise ValueError(code)


def _strings(value, *, empty=True):
    if not isinstance(value, list) or any(type(v) is not str or not v for v in value) or len(set(value)) != len(value) or not empty and not value:
        raise ValueError("registry.invalid_string_list")
    return tuple(value)


def _source_profile(declaration):
    if not isinstance(declaration, dict) or not _PROFILE_KEYS <= set(declaration):
        raise ValueError("registry.source_profile_invalid")
    return SourceProfile(declaration["profile_id"], declaration["kind"],
                         _strings(declaration["formats"]), declaration["scope"])


@lru_cache(maxsize=64)
def _profile_documents(owner):
    result = {}
    for kind, prefix, schemas in (
        ("profiles", "PROFILE_", {"stratbox.processing-profile", "stratbox.source-profile"}),
        ("families", "FAMILY_", {"stratbox.family"}),
    ):
        for resource in iter_resources(owner, kind):
            value = read_document(resource)
            schema = value.get("schema")
            if schema not in schemas:
                raise ValueError("registry.profile_schema_unknown")
            _shape(value, {"schema", "owner_id", "profile_id", "declaration"}, "registry.profile_invalid")
            if not isinstance(value["declaration"], dict):
                raise ValueError("registry.profile_invalid")
            if value["owner_id"] != owner:
                raise ValueError("registry.profile_owner_mismatch")
            if schema == "stratbox.source-profile":
                _shape(value["declaration"], _PROFILE_KEYS, "registry.source_profile_invalid", optional={"admission_ref", "implementation_ref", "implementation_parameters"})
                _source_profile(value["declaration"])
            if schema == "stratbox.processing-profile":
                _source_profile(value["declaration"])
            safe_token(value["profile_id"])
            if resource.name != prefix + value["profile_id"] + ".yaml":
                raise ValueError("registry.profile_filename_mismatch")
            if value["profile_id"] in result:
                raise ValueError("registry.profile_duplicate")
            result[value["profile_id"]] = value
    return result


def profile_document(owner, profile_id):
    """Return an isolated canonical profile, family or route declaration."""
    try:
        return copy.deepcopy(_profile_documents(owner)[profile_id])
    except KeyError:
        raise ValueError("registry.profile_unknown") from None


@dataclass(frozen=True, slots=True)
class SourceRoute:
    profile_id: str
    owner_id: str
    stages: tuple[ProcessingStage, ...]
    profiles: tuple[SourceProfile, ...]
    operations: tuple[SourceOperation, ...]
    qualifications: tuple[str, ...] = ()
    template_id: str | None = None
    slots: tuple[tuple[str, SourceOperation], ...] = ()

    def slot(self, name):
        try:
            return dict(self.slots)[name]
        except KeyError:
            raise ValueError("registry.source_slot_unknown") from None

    def binding(self, operation_id, *, format=None):
        result = next((item for item in self.operations if item.operation_id == operation_id), None)
        if result is None:
            raise ValueError("registry.source_operation_unbound")
        if format is not None and result.formats and format not in result.formats:
            raise ValueError("registry.source_operation_format_unavailable")
        return result


@lru_cache(maxsize=64)
def _template_documents(owner):
    result = {}
    for resource in iter_resources(owner, "templates"):
        value = read_document(resource)
        _shape(value, {"schema", "owner_id", "template_id", "slots", "stages"}, "registry.template_invalid")
        if value["schema"] != "stratbox.source-template" or value["owner_id"] != owner:
            raise ValueError("registry.template_owner_mismatch")
        identity = value["template_id"]
        safe_token(identity)
        if resource.name != "TEMPLATE_" + identity + ".yaml" or identity in result:
            raise ValueError("registry.template_identity_invalid")
        if not isinstance(value["slots"], dict) or not value["slots"]:
            raise ValueError("registry.template_slots_invalid")
        for slot, binding in value["slots"].items():
            safe_token(slot)
            _shape(binding, _OPERATION_REQUIRED, "registry.source_bindings_invalid", optional=_OPERATION_OPTIONAL)
        _strings(value["stages"])
        result[identity] = value
    return result


def template_document(owner, template_id):
    """Return shared source-slot defaults without loading domain implementations."""
    try:
        return copy.deepcopy(_template_documents(owner)[template_id])
    except KeyError:
        raise ValueError("registry.template_unknown") from None


def source_processing(value, *, owner, source_id):
    """Resolve template defaults and explicit source slot bindings deterministically."""
    _shape(value, {"template", "bindings", "profiles", "qualifications"}, "registry.processing_invalid")
    template = template_document(owner, value["template"])
    bindings = value["bindings"]
    if not isinstance(bindings, dict) or not set(bindings) <= set(template["slots"]):
        raise ValueError("registry.source_slot_unknown")
    slots = copy.deepcopy(template["slots"])
    for name, binding in bindings.items():
        _shape(binding, _OPERATION_REQUIRED, "registry.source_bindings_invalid", optional=_OPERATION_OPTIONAL)
        if binding["operation_id"] != slots[name]["operation_id"]:
            from stratbox.operations.declarations import metadata_definition
            before = metadata_definition(slots[name]["operation_id"]).processing
            after = metadata_definition(binding["operation_id"]).processing
            if before is None or after is None:
                raise ValueError("registry.source_slot_contract_mismatch")
            outputs = {port.name: port for port in after.outputs}
            inputs = {port.name: port for port in after.inputs}
            if (not set(before.stages) <= set(after.stages)
                    or any(port.name not in outputs or outputs[port.name].contract != port.contract
                           for port in before.outputs)
                    or any(port.required and (port.name not in inputs or inputs[port.name].contract != port.contract
                                               or inputs[port.name].collection != port.collection)
                           for port in before.inputs)
                    or any(port.required and port.name not in {entry.name for entry in before.inputs}
                           for port in after.inputs)):
                raise ValueError("registry.source_slot_contract_mismatch")
        slots[name] = copy.deepcopy(binding)
    route = decode_route({"schema": "stratbox.route", "owner_id": owner,
        "profile_id": source_id + ".route", "profiles": value["profiles"],
        "qualifications": value["qualifications"], "operations": list(slots.values()),
        "stages": template["stages"]}, owner=owner)
    from dataclasses import replace
    return replace(route, template_id=value["template"], slots=tuple(zip(slots, route.operations)))


def _expanded_route(value, *, owner):
    _shape(value, _ROUTE_KEYS, "registry.route_invalid", optional={"operations", "stages"})
    return copy.deepcopy(value)


def decode_route(value, *, owner) -> SourceRoute:
    value = _expanded_route(value, owner=owner)
    if value["schema"] != "stratbox.route" or value["owner_id"] != owner:
        raise ValueError("registry.route_invalid")
    safe_token(value["profile_id"])
    stages = tuple(ProcessingStage(s) for s in _strings(value["stages"]))
    profiles = []
    for reference in _strings(value["profiles"]):
        metadata = profile_document(owner, reference)
        if metadata["schema"] not in {"stratbox.source-profile", "stratbox.processing-profile"}:
            raise ValueError("registry.route_profile_schema_invalid")
        profiles.append(_source_profile(metadata["declaration"]))
    if len({p.profile_id for p in profiles}) != len(profiles):
        raise ValueError("registry.route_profiles_invalid")
    operations = []
    if not isinstance(value["operations"], list):
        raise ValueError("registry.source_bindings_invalid")
    for binding in value["operations"]:
        _shape(binding, _OPERATION_REQUIRED, "registry.source_bindings_invalid", optional=_OPERATION_OPTIONAL)
        pairs = binding.get("parameters", [])
        auxiliaries = binding.get("auxiliary_sources", {})
        if (not isinstance(pairs, list) or any(not isinstance(pair, list) for pair in pairs)
                or not isinstance(auxiliaries, dict)):
            raise ValueError("registry.source_bindings_invalid")
        operations.append(SourceOperation(binding["operation_id"], binding.get("state", "supported"),
            binding.get("reason", ""), tuple(tuple(pair) for pair in pairs), _strings(binding.get("formats", [])),
            binding.get("identity_parameter"), tuple((port, _strings(identities, empty=False)) for port, identities in auxiliaries.items()),
            binding.get("context_scope", "source")))
    if len({o.operation_id for o in operations}) != len(operations):
        raise ValueError("registry.source_bindings_invalid")
    return SourceRoute(value["profile_id"], owner, stages, tuple(profiles), tuple(operations), _strings(value["qualifications"]))


def decode_source_group(value):
    required = {"group_id", "title", "contracts"}
    optional = {"outputs", "profile_ids", "formats", "grain", "period_model", "source_table_code", "qualification", "layout_editions", "semantic_profile_editions"}
    _shape(value, required, "registry.source_group_invalid", optional=optional)
    contracts = []
    if not isinstance(value["contracts"], list):
        raise ValueError("registry.source_group_contracts_invalid")
    for contract in value["contracts"]:
        _shape(contract, {"schema_id"}, "registry.source_group_contracts_invalid", optional={"version", "role"})
        contracts.append(DataContract(contract["schema_id"], contract.get("version", 1), DataRole(contract["role"]) if contract.get("role") else None))
    outputs = value.get("outputs", [])
    if not isinstance(outputs, list):
        raise ValueError("registry.source_group_outputs_invalid")
    from stratbox.operations.declarations import metadata_definition
    for output in outputs:
        _shape(output, {"operation_id", "port"}, "registry.source_group_outputs_invalid")
        definition = metadata_definition(output["operation_id"])
        port = next((port for port in definition.processing.outputs if port.name == output["port"]), None) if definition.processing else None
        if port is None or port.contract in contracts:
            raise ValueError("registry.source_group_output_unavailable")
        contracts.append(port.contract)
    options = dict(value)
    options.pop("outputs", None)
    options["contracts"] = tuple(contracts)
    for name in ("profile_ids", "formats", "grain", "layout_editions", "semantic_profile_editions"):
        options[name] = _strings(options.get(name, []))
    return SourceGroup(**options)


_PROFILE_KINDS = {
    "acquisition_profile": {"acquisition"}, "extraction_profile": {"extraction"},
    "extract_profile": {"physical_extract", "extraction"}, "normalization_profile": {"source_projection"},
    "table_profile": {"source_table", "table"}, "integration_profile": {"integration"},
    "product_profile": {"product"}, "discovery": {"discovery"}, "table": {"table", "source_table"},
}


def _publication_profile_refs(value):
    for name, reference in value["publication"].items():
        if name.endswith("_profile") and reference is not None:
            yield name, reference
        elif name == "profiles":
            if not isinstance(reference, dict):
                raise ValueError("registry.source_profile_references_invalid")
            yield from reference.items()


def _profile_pointer(owner, reference):
    if not isinstance(reference, str) or reference.count(":") != 1:
        raise ValueError("registry.source_profile_pointer_invalid")
    module, symbol = reference.split(":")
    boundary = "stratbox.core" if owner.startswith("core.") else "stratbox.domains." + owner
    if not (module == boundary or module.startswith(boundary + ".")) or not all(part.isidentifier() for part in (*module.split("."), *symbol.split("."))):
        raise ValueError("registry.source_profile_pointer_owner_mismatch")


def validate_publication_profiles(value, *, typed=False):
    owner = value["owner_id"]
    domain, external = value.get("domain_profiles", {}), value.get("external_profiles", {})
    if not isinstance(domain, dict) or not isinstance(external, dict) or set(domain) & set(external):
        raise ValueError("registry.source_profile_references_invalid")
    for profile_id, pointer in domain.items():
        safe_token(profile_id)
        _shape(pointer, {"kind", "implementation_ref", "implementation_parameters"}, "registry.source_profile_pointer_invalid")
        _profile_pointer(owner, pointer["implementation_ref"])
        if (not isinstance(pointer["implementation_parameters"], dict) or not isinstance(pointer["kind"], str)
                or any(not isinstance(key, str) or not key.isidentifier() for key in pointer["implementation_parameters"])):
            raise ValueError("registry.source_profile_pointer_invalid")
        if typed:
            from importlib import import_module
            from inspect import signature
            module, symbol = pointer["implementation_ref"].split(":")
            implementation = import_module(module)
            for component in symbol.split("."):
                implementation = getattr(implementation, component)
            signature(implementation).bind(**pointer["implementation_parameters"])
            resolved = implementation(**pointer["implementation_parameters"])
            if getattr(resolved, "profile_id", None) != profile_id:
                raise ValueError("registry.source_profile_pointer_identity_mismatch")
    for profile_id, pointer in external.items():
        safe_token(profile_id)
        _shape(pointer, {"kind", "reason"}, "registry.source_external_profile_invalid")
        if not isinstance(pointer["kind"], str) or not isinstance(pointer["reason"], str) or not pointer["reason"].strip():
            raise ValueError("registry.source_external_profile_invalid")
    used = set()
    for name, reference in _publication_profile_refs(value):
        safe_token(reference)
        used.add(reference)
        if reference in domain:
            kind = domain[reference]["kind"]
        elif reference in external:
            kind = external[reference]["kind"]
        else:
            try:
                profile = profile_document(owner, reference)
            except ValueError as error:
                if str(error) == "registry.profile_unknown":
                    raise ValueError("registry.source_profile_unknown") from None
                raise
            if profile["schema"] not in {"stratbox.source-profile", "stratbox.processing-profile"}:
                raise ValueError("registry.source_profile_kind_invalid")
            kind = profile["declaration"]["kind"]
        if name in _PROFILE_KINDS and kind not in _PROFILE_KINDS[name]:
            raise ValueError("registry.source_profile_kind_invalid")
    if not (set(domain) | set(external)) <= used:
        raise ValueError("registry.source_profile_pointer_unused")


@lru_cache(maxsize=64)
def _sources(owner):
    values = []
    seen = set()
    for resource in iter_resources(owner, "sources"):
        value = read_document(resource)
        _shape(value, _SOURCE_KEYS, "registry.source_invalid", optional={"domain_profiles", "external_profiles"})
        if value["schema"] != "stratbox.source" or value["owner_id"] != owner:
            raise ValueError("registry.source_invalid")
        for key in ("publisher_id", "family_id", "series_id"):
            safe_token(value[key])
        if resource.name != "SOURCE_" + value["series_id"] + ".yaml":
            raise ValueError("registry.source_filename_mismatch")
        if (value["series_id"] in seen or not isinstance(value["publication"], dict)
                or type(value["position"]) is not int or value["position"] < 0):
            raise ValueError("registry.source_invalid")
        if set(value["publication"]) & {"owner_id", "publisher_id", "family_id", "series_id", "source_id", "title", "formats", "issue_model", "route_profile"}:
            raise ValueError("registry.publication_identity_duplicate")
        validate_publication_profiles(value)
        seen.add(value["series_id"])
        route = source_processing(value["processing"], owner=owner, source_id=value["series_id"])
        formats = _strings(value["formats"], empty=False)
        if any(binding.formats and not set(binding.formats) <= set(formats) for binding in route.operations):
            raise ValueError("registry.source_binding_formats_invalid")
        family = value["family_profile"]
        if family is not None:
            safe_token(family)
            document = profile_document(owner, family)
            if document["schema"] != "stratbox.family" or document["declaration"].get("family_id") != value["family_id"]:
                raise ValueError("registry.source_family_profile_invalid")
        if not isinstance(value["source_groups"], list) or not value["source_groups"]:
            raise ValueError("registry.source_groups_required")
        operation_ids = {binding.operation_id for binding in route.operations}
        if any(output.get("operation_id") not in operation_ids
               for group in value["source_groups"] if isinstance(group, dict)
               for output in group.get("outputs", []) if isinstance(output, dict)):
            raise ValueError("registry.source_group_output_unbound")
        groups = tuple(decode_source_group(group) for group in value["source_groups"])
        if any(not set(group.formats) <= set(formats) for group in groups):
            raise ValueError("registry.source_group_formats_invalid")
        for group in groups:
            for reference in group.profile_ids:
                profile_document(owner, reference)
        card = SourceCard(value["publisher_id"], value["family_id"], value["series_id"], value["title"], value["issue_model"], formats, route.profiles, route.operations, route.qualifications, groups)
        values.append((value, card, route))
    return tuple(sorted(values, key=lambda item: item[1].series_id))


def source_documents(owner) -> tuple[dict, ...]:
    return tuple(copy.deepcopy(value) for value, _, _ in _sources(owner))


def source_cards(owner) -> tuple[SourceCard, ...]:
    return tuple(card for _, card, _ in _sources(owner))


@lru_cache(maxsize=1)
def _route_index():
    routes = {}
    for owner in resource_owners():
        for _, card, route in _sources(owner):
            if card.series_id in routes:
                raise ValueError("registry.source_duplicate")
            routes[card.series_id] = route
    return MappingProxyType(routes)


def source_group(series_id, group_id) -> SourceGroup:
    for owner in resource_owners():
        for _, card, _ in _sources(owner):
            if card.series_id == series_id:
                for group in card.source_groups:
                    if group.group_id == group_id:
                        return group
                raise ValueError("registry.source_group_unknown")
    raise ValueError("registry.source_unknown")


def source_route(series_id) -> SourceRoute:
    try:
        return _route_index()[series_id]
    except (KeyError, TypeError):
        raise ValueError("registry.source_unknown") from None


def publication_families(owner, *, series_fields=()) -> tuple[dict, ...]:
    """Project substantive publisher families from canonical atomic sources."""
    grouped = {}
    for value, _, _ in sorted(_sources(owner), key=lambda item: item[0]["position"]):
        profile = value["family_profile"]
        if profile is None:
            continue
        if profile not in grouped:
            grouped[profile] = copy.deepcopy(profile_document(owner, profile)["declaration"])
            grouped[profile]["series"] = []
        declaration = copy.deepcopy(value["publication"])
        for target, source in series_fields:
            if target in declaration:
                raise ValueError("registry.publication_field_duplicate")
            declaration[target] = copy.deepcopy(value[source])
        grouped[profile]["series"].append(declaration)
    return tuple(grouped.values())


def validate_source_bindings(operation_catalog):
    """Validate declared source applicability against exact operation facts."""
    seen = set()
    count = 0
    owners = {r.owner_id for r in operation_catalog.registrations}
    for owner in resource_owners():
        if owner not in owners:
            raise ValueError("registry.source_owner_unregistered")
        for group in _template_documents(owner).values():
            for binding in group["slots"].values():
                definition = operation_catalog.get(binding["operation_id"])
                parameters = set(definition.processing.parameters if definition.processing else ())
                if not {key for key, _ in binding.get("parameters", [])} <= parameters:
                    raise ValueError("registry.source_parameter_unavailable")
                if binding.get("identity_parameter") is not None and binding["identity_parameter"] not in parameters:
                    raise ValueError("registry.source_identity_parameter_unavailable")
                if definition.processing is not None and not set(definition.processing.stages) <= {ProcessingStage(stage) for stage in group["stages"]}:
                    raise ValueError("registry.group_stage_unavailable")
        for profile in _profile_documents(owner).values():
            if profile["schema"] != "stratbox.processing-profile":
                continue
            declaration = profile["declaration"]
            if "operation_id" in declaration:
                operation_catalog.reference(declaration["operation_id"])
            for field in ("alignment_operation", "view_operation"):
                identity = declaration.get(field)
                if identity is not None:
                    operation_catalog.reference(identity)
        for source_document, card, route in _sources(owner):
            validate_publication_profiles(source_document, typed=True)
            if card.series_id in seen:
                raise ValueError("registry.source_duplicate")
            seen.add(card.series_id)
            for binding in route.operations:
                definition = operation_catalog.get(binding.operation_id)
                if not {key for key, _ in binding.parameters} <= set(definition.processing.parameters if definition.processing else ()):
                    raise ValueError("registry.source_parameter_unavailable")
                if binding.identity_parameter is not None and binding.identity_parameter not in set(definition.processing.parameters if definition.processing else ()):
                    raise ValueError("registry.source_identity_parameter_unavailable")
                if definition.processing is not None and not set(definition.processing.stages) <= set(route.stages):
                    raise ValueError("registry.source_stage_unavailable")
            count += 1
    return count


def validate_source_metadata(catalog):
    """Check all inert source/group/route/profile links without loading Python."""
    registered = {registration.owner_id for registration in catalog.registrations}
    count = 0
    domain_profiles = {}
    for owner in resource_owners():
        if owner not in registered:
            continue
        for group in _template_documents(owner).values():
            for binding in group["slots"].values():
                catalog.reference(binding["operation_id"])
        for document, card, route in _sources(owner):
            for profile_id, pointer in document.get("domain_profiles", {}).items():
                key = owner, profile_id
                if key in domain_profiles and domain_profiles[key] != pointer:
                    raise ValueError("registry.source_domain_profile_conflict")
                domain_profiles[key] = pointer
            for binding in card.operations:
                definition = catalog.metadata(binding.operation_id)
                parameters = set(definition.processing.parameters) if definition.processing else set()
                if not {name for name, _ in binding.parameters} <= parameters:
                    raise ValueError("registry.source_parameter_unavailable")
                if binding.identity_parameter is not None and binding.identity_parameter not in parameters:
                    raise ValueError("registry.source_identity_parameter_unavailable")
                ports = {port.name for port in definition.processing.inputs} if definition.processing else set()
                if not {port for port, _ in binding.auxiliary_sources} <= ports:
                    raise ValueError("registry.source_auxiliary_port_unknown")
            count += 1
    from stratbox.domains.registry.requirements import _requirements, validate_source_assembly
    from stratbox.operations.declarations import operation_document
    for ref in catalog.references:
        if ref.definition is not None:
            continue
        _requirements(catalog, ref.operation_id, typed=False)
        document = operation_document(ref.operation_id)
        validate_source_assembly(document.get("source_assembly", {}), owner_id=document["owner_id"])
    return count


def validate_source_group_editions(owner, group):
    """A declared physical layout edition resolves to an actual profile owner."""
    if not group.layout_editions:
        return
    from importlib import import_module
    from inspect import signature
    actual = set()
    for profile_id in group.profile_ids:
        declaration = profile_document(owner, profile_id)["declaration"]
        reference = declaration.get("implementation_ref")
        if reference is None:
            continue
        _profile_pointer(owner, reference)
        module, name = reference.split(":")
        implementation = import_module(module)
        for component in name.split("."):
            implementation = getattr(implementation, component)
        parameters = declaration.get("implementation_parameters", {})
        if callable(implementation) and parameters:
            signature(implementation).bind(**parameters)
            implementation = implementation(**parameters)
        edition = getattr(implementation, "edition", None)
        if isinstance(edition, str):
            actual.add(edition)
    if not set(group.layout_editions) <= actual:
        raise ValueError("registry.source_group_layout_unresolved")


def validate_source_links(catalog):
    """Admit concrete operation policies and role-assembly Python type links."""
    count = validate_source_bindings(catalog)
    for registration in catalog.registrations:
        for card in source_cards(registration.owner_id):
            for group in card.source_groups:
                validate_source_group_editions(registration.owner_id, group)
    from stratbox.domains.registry.requirements import validate_requirement_links
    for ref in catalog.references:
        validate_requirement_links(catalog, ref.operation_id)
    return count


_RESOLVING_DOMAIN_PROFILES = ContextVar("stratbox_resolving_domain_profiles", default=frozenset())


def resolve_domain_profile(owner, profile_id):
    """Resolve an explicitly declared domain-owned profile factory.

    Applications can add source parameters for an existing compatible factory;
    source lookup does not require another Python identity allowlist.
    """
    try:
        safe_token(owner)
        safe_token(profile_id)
    except ValueError:
        raise ValueError("registry.source_profile_identity_invalid") from None
    pointers = [document.get("domain_profiles", {}).get(profile_id) for document in source_documents(owner)]
    pointers = [pointer for pointer in pointers if pointer is not None]
    if not pointers:
        raise ValueError("registry.source_domain_profile_unknown")
    if any(pointer != pointers[0] for pointer in pointers):
        raise ValueError("registry.source_domain_profile_conflict")
    key = owner, profile_id
    if key in _RESOLVING_DOMAIN_PROFILES.get():
        raise ValueError("registry.source_profile_factory_cycle")
    pointer = pointers[0]
    _profile_pointer(owner, pointer["implementation_ref"])
    from importlib import import_module
    from inspect import signature
    module, symbol = pointer["implementation_ref"].split(":")
    factory = import_module(module)
    for component in symbol.split("."):
        factory = getattr(factory, component)
    signature(factory).bind(**pointer["implementation_parameters"])
    token = _RESOLVING_DOMAIN_PROFILES.set(_RESOLVING_DOMAIN_PROFILES.get() | {key})
    try:
        value = factory(**pointer["implementation_parameters"])
    finally:
        _RESOLVING_DOMAIN_PROFILES.reset(token)
    if getattr(value, "profile_id", None) != profile_id:
        raise ValueError("registry.source_profile_pointer_identity_mismatch")
    return value
