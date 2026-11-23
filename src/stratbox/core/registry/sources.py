"""Canonical sources, route applicability and independently owned profiles.

Stages describe processing classes. Exact port contracts decide value handoff;
source bindings retain publisher-specific applicability and qualifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import copy
from types import MappingProxyType

from stratbox.shared.identifiers import safe_token
from stratbox.shared.data.operations import ProcessingStage
from stratbox.core.registry.resources import iter_resources, read_document, resource_owners
from stratbox.core.registry.source_catalog import SourceCard, SourceProfile, SourceOperation

_SOURCE_KEYS = {"schema", "owner_id", "publisher_id", "family_id", "series_id", "title", "issue_model", "formats", "route_profile", "family_profile", "position", "publication"}
_ROUTE_KEYS = {"schema", "owner_id", "profile_id", "profiles", "qualifications"}
_ROUTE_OPTIONAL = {"operations", "stages", "transitions", "groups"}
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
        ("routes", "ROUTE_", {"stratbox.route"}),
        ("profiles", "PROFILE_", {"stratbox.processing-profile", "stratbox.source-profile"}),
        ("families", "FAMILY_", {"stratbox.family"}),
    ):
        for resource in iter_resources(owner, kind):
            value = read_document(resource)
            schema = value.get("schema")
            if schema not in schemas:
                raise ValueError("registry.profile_schema_unknown")
            if schema == "stratbox.route":
                _shape(value, _ROUTE_KEYS, "registry.route_invalid", optional=_ROUTE_OPTIONAL)
            else:
                _shape(value, {"schema", "owner_id", "profile_id", "declaration"}, "registry.profile_invalid")
                if not isinstance(value["declaration"], dict):
                    raise ValueError("registry.profile_invalid")
            if value["owner_id"] != owner:
                raise ValueError("registry.profile_owner_mismatch")
            if schema == "stratbox.source-profile":
                _shape(value["declaration"], _PROFILE_KEYS, "registry.source_profile_invalid")
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
    transitions: tuple[tuple[ProcessingStage, ProcessingStage], ...]
    profiles: tuple[SourceProfile, ...]
    operations: tuple[SourceOperation, ...]
    qualifications: tuple[str, ...] = ()

    def allows(self, previous, following) -> bool:
        try:
            edge = ProcessingStage(previous), ProcessingStage(following)
        except (TypeError, ValueError):
            return False
        return edge in self.transitions

    def binding(self, operation_id, *, format=None):
        result = next((item for item in self.operations if item.operation_id == operation_id), None)
        if result is None:
            raise ValueError("registry.source_operation_unbound")
        if format is not None and result.formats and format not in result.formats:
            raise ValueError("registry.source_operation_format_unavailable")
        return result


@lru_cache(maxsize=64)
def _group_documents(owner):
    result = {}
    for resource in iter_resources(owner, "groups"):
        value = read_document(resource)
        _shape(value, {"schema", "owner_id", "group_id", "operations", "stages", "transitions"}, "registry.group_invalid")
        if value["schema"] != "stratbox.processing-group" or value["owner_id"] != owner:
            raise ValueError("registry.group_owner_mismatch")
        safe_token(value["group_id"])
        if resource.name != "GROUP_" + value["group_id"] + ".yaml":
            raise ValueError("registry.group_filename_mismatch")
        if value["group_id"] in result:
            raise ValueError("registry.group_duplicate")
        body = {"schema": "stratbox.route", "owner_id": owner, "profile_id": value["group_id"],
                "profiles": [], "qualifications": [], **{name: value[name] for name in ("operations", "stages", "transitions")}}
        decode_route(body, owner=owner)
        result[value["group_id"]] = value
    return result


def group_document(owner, group_id):
    """Return an isolated shared transformation group; nested groups are absent."""
    try:
        return copy.deepcopy(_group_documents(owner)[group_id])
    except KeyError:
        raise ValueError("registry.group_unknown") from None


def _expanded_route(value, *, owner):
    _shape(value, _ROUTE_KEYS, "registry.route_invalid", optional=_ROUTE_OPTIONAL)
    groups = _strings(value.get("groups", []))
    body = copy.deepcopy(value)
    body.pop("groups", None)
    bodies = [group_document(owner, identity) for identity in groups] + [value]
    for name in ("operations", "stages", "transitions"):
        parts = []
        for part in bodies:
            items = part.get(name, [])
            if not isinstance(items, list):
                raise ValueError("registry.route_invalid")
            if name == "stages":
                items = _strings(items)
                parts.extend(item for item in items if item not in parts)
            else:
                parts.extend(copy.deepcopy(items))
        body[name] = parts
    return body


def decode_route(value, *, owner) -> SourceRoute:
    value = _expanded_route(value, owner=owner)
    if value["schema"] != "stratbox.route" or value["owner_id"] != owner:
        raise ValueError("registry.route_invalid")
    safe_token(value["profile_id"])
    stages = tuple(ProcessingStage(s) for s in _strings(value["stages"]))
    transitions = []
    if not isinstance(value["transitions"], list):
        raise ValueError("registry.route_transitions_invalid")
    for edge in value["transitions"]:
        _shape(edge, {"from", "to"}, "registry.route_transitions_invalid")
        pair = ProcessingStage(edge["from"]), ProcessingStage(edge["to"])
        if not set(pair) <= set(stages) or pair in transitions:
            raise ValueError("registry.route_transitions_invalid")
        transitions.append(pair)
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
    return SourceRoute(value["profile_id"], owner, stages, tuple(transitions), tuple(profiles), tuple(operations), _strings(value["qualifications"]))


@lru_cache(maxsize=64)
def _sources(owner):
    values = []
    seen = set()
    for resource in iter_resources(owner, "sources"):
        value = read_document(resource)
        _shape(value, _SOURCE_KEYS, "registry.source_invalid")
        if value["schema"] != "stratbox.source" or value["owner_id"] != owner:
            raise ValueError("registry.source_invalid")
        for key in ("publisher_id", "family_id", "series_id", "route_profile"):
            safe_token(value[key])
        if resource.name != "SOURCE_" + value["series_id"] + ".yaml":
            raise ValueError("registry.source_filename_mismatch")
        if (value["series_id"] in seen or not isinstance(value["publication"], dict)
                or type(value["position"]) is not int or value["position"] < 0):
            raise ValueError("registry.source_invalid")
        if set(value["publication"]) & {"owner_id", "publisher_id", "family_id", "series_id", "source_id", "title", "formats", "issue_model", "route_profile"}:
            raise ValueError("registry.publication_identity_duplicate")
        seen.add(value["series_id"])
        route = decode_route(profile_document(owner, value["route_profile"]), owner=owner)
        formats = _strings(value["formats"], empty=False)
        if any(binding.formats and not set(binding.formats) <= set(formats) for binding in route.operations):
            raise ValueError("registry.source_binding_formats_invalid")
        family = value["family_profile"]
        if family is not None:
            safe_token(family)
            document = profile_document(owner, family)
            if document["schema"] != "stratbox.family" or document["declaration"].get("family_id") != value["family_id"]:
                raise ValueError("registry.source_family_profile_invalid")
        card = SourceCard(value["publisher_id"], value["family_id"], value["series_id"], value["title"], value["issue_model"], formats, route.profiles, route.operations, route.qualifications)
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
        for group in _group_documents(owner).values():
            for binding in group["operations"]:
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
        for _, card, route in _sources(owner):
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
