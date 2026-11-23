"""Named source dependencies and non-executing, instance-aware readiness.

Requirement records describe semantic roles. Resolved instances identify the
actual publication and material selected for each role. Domain algorithms retain
responsibility for scientific interpretation after these common checks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache
from math import isfinite
from typing import Mapping, get_type_hints, get_args, get_origin
from importlib import import_module
from dataclasses import fields, is_dataclass, replace

from stratbox.shared.data.sources import SourceInstance, ResolvedSourceInstance, MaterialAdmission, DomainAdmission

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.identifiers import safe_token

_COMPATIBILITY_FIELDS = {"report_date", "publication_step", "perimeter"}


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    input_name: str
    source_ids: tuple[str, ...]
    accepted_contracts: tuple[DataContract, ...]
    role: str
    port: str
    group_id: str | None = None
    required: bool = True
    minimum: int = 1
    maximum: int | None = 1
    compatibility: tuple[str, ...] = ()
    source_label: str | None = None
    profile_ids: tuple[str, ...] = ()
    grain: tuple[str, ...] = ()
    layout_editions: tuple[str, ...] = ()
    semantic_profile_editions: tuple[str, ...] = ()
    allow_cross_owner: bool = False

    def __post_init__(self):
        for token in (self.input_name, self.role, self.port):
            safe_token(token)
        for token in (self.group_id, self.source_label):
            if token is not None:
                safe_token(token)
        if (not isinstance(self.source_ids, tuple) or not self.source_ids
                or len(set(self.source_ids)) != len(self.source_ids)
                or not isinstance(self.accepted_contracts, tuple) or not self.accepted_contracts
                or any(not isinstance(item, DataContract) for item in self.accepted_contracts)
                or len(set(self.accepted_contracts)) != len(self.accepted_contracts)
                or type(self.required) is not bool or type(self.minimum) is not int or self.minimum < 0
                or self.required and self.minimum < 1
                or self.maximum is not None and (type(self.maximum) is not int or self.maximum < self.minimum)
                or not isinstance(self.compatibility, tuple)
                or not set(self.compatibility) <= _COMPATIBILITY_FIELDS
                or len(set(self.compatibility)) != len(self.compatibility)):
            raise ValueError("registry.source_requirement_invalid")
        if type(self.allow_cross_owner) is not bool:
            raise ValueError("registry.source_requirement_invalid")
        for values in (self.profile_ids, self.grain, self.layout_editions, self.semantic_profile_editions):
            if not isinstance(values, tuple) or any(not isinstance(value, str) for value in values) or len(set(values)) != len(values):
                raise ValueError("registry.source_requirement_invalid")
            for value in values:
                safe_token(value)
        for identity in self.source_ids:
            safe_token(identity)


@dataclass(frozen=True, slots=True)
class ReadinessLayers:
    declaration: str = "known"
    applicability: str = "supported"
    instances: str = "supplied"
    structure: str = "unverified"
    material: str = "unverified"
    domain: str = "unassessed"
    environment: str = "not_checked"
    effects: str = "not_checked"


@dataclass(frozen=True, slots=True)
class RequirementAssessment:
    requirement: SourceRequirement
    instances: tuple[SourceInstance, ...]
    state: str
    reasons: tuple[str, ...] = ()
    layers: ReadinessLayers = ReadinessLayers()
    materials: tuple[MaterialAdmission, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationReadiness:
    operation_id: str
    requirements: tuple[RequirementAssessment, ...]
    unexpected_inputs: tuple[str, ...] = ()
    environment: str = "not_checked"
    effects: str = "not_checked"
    scope: str = "source_requirements"

    @property
    def required_count(self):
        return sum(item.requirement.required for item in self.requirements)

    @property
    def supplied_count(self):
        return sum(item.requirement.required and bool(item.instances) for item in self.requirements)

    @property
    def ready_count(self):
        return sum(item.requirement.required and item.state in {"requirements_satisfied", "admitted"} for item in self.requirements)

    @property
    def state(self):
        if self.unexpected_inputs or any(item.state in {"missing", "incompatible", "rejected"} for item in self.requirements) or self.environment == "unavailable" or self.effects == "unavailable":
            return "blocked"
        if any(item.state in {"unqualified", "requirements_satisfied"} for item in self.requirements):
            return "conditional"
        if self.environment == "available" and self.effects in {"authorized", "not_required"}:
            return "ready_to_execute"
        return "inputs_verified" if self.requirements else "requirements_satisfied"

    @property
    def layers(self):
        active = [item.layers for item in self.requirements if item.state != "optional_missing"]
        def aggregate(name, good, empty):
            values = {getattr(item, name) for item in active}
            return empty if not values else next(iter(values)) if len(values) == 1 else good.split("|")[0] if values <= set(good.split("|")) else "mixed"
        return ReadinessLayers(
            declaration="known", applicability=aggregate("applicability", "supported", "supported"),
            instances=aggregate("instances", "supplied", "not_required"),
            structure=aggregate("structure", "valid", "not_required"),
            material=aggregate("material", "verified|not_required", "not_required"),
            domain=aggregate("domain", "admitted|not_required", "not_required"),
            environment=self.environment, effects=self.effects)


def decode_requirement(value):
    required = {"input_name", "source_ids", "accepted_contracts", "role", "port"}
    optional = {"group_id", "required", "minimum", "maximum", "compatibility", "source_label", "profile_ids", "grain", "layout_editions", "semantic_profile_editions", "allow_cross_owner"}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional:
        raise ValueError("registry.source_requirement_invalid")
    options = dict(value)
    for name in ("source_ids", "accepted_contracts", "compatibility"):
        if not isinstance(options.get(name, []), list):
            raise ValueError("registry.source_requirement_invalid")
    contracts = []
    for contract in options["accepted_contracts"]:
        if not isinstance(contract, dict) or not {"schema_id"} <= set(contract) or set(contract) - {"schema_id", "version", "role"}:
            raise ValueError("registry.source_requirement_invalid")
        contracts.append(DataContract(contract["schema_id"], contract.get("version", 1),
                                     DataRole(contract["role"]) if contract.get("role") else None))
    options["source_ids"] = tuple(options["source_ids"])
    options["accepted_contracts"] = tuple(contracts)
    options["compatibility"] = tuple(options.get("compatibility", []))
    for name in ("profile_ids", "grain", "layout_editions", "semantic_profile_editions"):
        if not isinstance(options.get(name, []), list):
            raise ValueError("registry.source_requirement_invalid")
        options[name] = tuple(options.get(name, []))
    if options.get("required") is False and "minimum" not in options:
        options["minimum"] = 0
    return SourceRequirement(**options)


@lru_cache(maxsize=4096)
def declared_requirements(operation_id):
    """Decode dependency facts without importing an operation implementation."""
    from stratbox.operations.declarations import operation_document
    values = operation_document(operation_id).get("source_requirements", [])
    if not isinstance(values, list):
        raise ValueError("registry.source_requirements_invalid")
    requirements = tuple(decode_requirement(value) for value in values)
    if len({item.input_name for item in requirements}) != len(requirements):
        raise ValueError("registry.source_requirement_duplicate")
    return requirements


def _requirements(catalog, operation_id, *, typed):
    """Resolve declared roles against registered ports and canonical sources."""
    operation = catalog.get(operation_id) if typed else catalog.metadata(operation_id)
    if catalog.reference(operation_id).definition is not None:
        return ()
    requirements = declared_requirements(operation_id)
    if not requirements:
        return ()
    from stratbox.domains.registry.declarations import source_documents, source_group
    sources = {source["series_id"]: source for owner in {item.owner_id for item in catalog.registrations}
               for source in source_documents(owner)}
    ports = {port.name for port in operation.processing.inputs} if operation.processing else set()
    operation_owner = catalog.owner_of(operation_id)
    for requirement in requirements:
        if requirement.port not in ports:
            raise ValueError("registry.source_requirement_port_unknown")
        if not set(requirement.source_ids) <= set(sources):
            raise ValueError("registry.source_requirement_source_unknown")
        for identity in requirement.source_ids:
            if operation_owner != sources[identity]["owner_id"] and not requirement.allow_cross_owner:
                raise ValueError("registry.source_requirement_cross_owner")
            if requirement.group_id is not None:
                group = source_group(identity, requirement.group_id)
                if not set(requirement.accepted_contracts) <= set(group.contracts):
                    raise ValueError("registry.source_requirement_contract_unavailable")
                if not set(requirement.profile_ids) <= set(group.profile_ids):
                    raise ValueError("registry.source_requirement_profile_unavailable")
                if requirement.grain and requirement.grain != group.grain:
                    raise ValueError("registry.source_requirement_grain_mismatch")
                if requirement.layout_editions and not set(requirement.layout_editions) <= set(group.layout_editions):
                    raise ValueError("registry.source_requirement_layout_unavailable")
                if requirement.semantic_profile_editions and not set(requirement.semantic_profile_editions) <= set(group.semantic_profile_editions):
                    raise ValueError("registry.source_requirement_semantics_unavailable")
    return requirements


def operation_requirements(catalog, operation_id):
    return _requirements(catalog, operation_id, typed=False)


def describe_source_requirements(catalog, operation_id):
    return tuple(asdict(item) for item in _requirements(catalog, operation_id, typed=False))


def _prepared(value, contract=None):
    from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput, prepare_input
    if isinstance(value, (PreparedInput, ProjectedOutput)):
        return value
    return prepare_input(value, contract)


def _instance_from_prepared(requirement, value):
    from stratbox.core.execution.value_context import value_context
    context = getattr(value, "source_context", None) or value_context(value.value, value.contract)
    if len(context.source_ids) != 1:
        raise ValueError("source.role_context_missing_or_ambiguous")
    source_id = context.source_ids[0]
    from stratbox.domains.registry.declarations import source_group
    uses = tuple(use for use in getattr(context, "uses", ()) if use.coordinate.source_id == source_id)
    groups = {use.coordinate.source_group_id for use in uses if use.coordinate.source_group_id is not None}
    if len(groups) > 1:
        raise ValueError("source.role_group_ambiguous")
    group_id = next(iter(groups)) if groups else None
    actual_group = source_group(source_id, group_id) if group_id is not None else None
    coordinate = uses[0].coordinate if len(uses) == 1 else None
    return SourceInstance(source_id, value.contract, group_id=group_id,
        issue_id=getattr(coordinate, "issue_id", None),
        source_material_identity=getattr(coordinate, "material_identity", None),
        consumed_identity=value.identity,
        layout_edition=getattr(coordinate, "layout_edition", None),
        semantic_profile_edition=getattr(coordinate, "semantic_profile_edition", None),
        grain=actual_group.grain if actual_group else ())


def _actual_resolution(requirement, incoming, resolver=None):
    """Return claims plus actual prepared data, without accepting claimed flags."""
    from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
    from stratbox.shared.evidence import SourcePayload
    if isinstance(incoming, (PreparedInput, ProjectedOutput)):
        instance = _instance_from_prepared(requirement, incoming)
        return instance, incoming, incoming.value if isinstance(incoming.value, SourcePayload) else None, None
    if isinstance(incoming, ResolvedSourceInstance):
        return incoming.instance, _prepared(incoming.value, incoming.instance.contract), incoming.material, incoming.receipt
    if not isinstance(incoming, SourceInstance):
        raise ValueError("registry.source_instances_invalid")
    if resolver is None:
        return incoming, None, None, None
    try:
        result = resolver.resolve(incoming) if hasattr(resolver, "resolve") else resolver(incoming)
    except (OSError, KeyError, FileNotFoundError):
        return incoming, None, None, "inaccessible"
    if isinstance(result, bytes):
        result = SourcePayload(result)
    if isinstance(result, SourcePayload):
        return incoming, _prepared(result, incoming.contract), result, None
    if not isinstance(result, ResolvedSourceInstance) or result.instance != incoming:
        raise ValueError("source.resolver_result_invalid")
    return incoming, _prepared(result.value, incoming.contract), result.material, result.receipt


def _material_admission(instance, prepared, material, receipt):
    from stratbox.core.execution.values import value_identity
    from stratbox.shared.evidence import SourcePayload
    if receipt == "inaccessible":
        return MaterialAdmission("inaccessible", instance.material_identity, reasons=("source.material_inaccessible",))
    if prepared is None:
        return MaterialAdmission("unverified", instance.material_identity, reasons=("source.material_unverified",))
    if instance.contract.schema_id in {"source.payload", "material.payload"} and not isinstance(prepared.value, SourcePayload):
        return MaterialAdmission("mismatch", instance.material_identity, reasons=("source.material_value_type_mismatch",))
    if prepared.contract != instance.contract:
        return MaterialAdmission("mismatch", instance.material_identity, reasons=("source.resolved_contract_mismatch",))
    actual_value_identity = value_identity(prepared.value)
    if prepared.identity is not None and prepared.identity != actual_value_identity:
        return MaterialAdmission("mismatch", instance.material_identity, reasons=("source.prepared_identity_mismatch",))
    if instance.consumed_identity is not None and instance.consumed_identity != actual_value_identity:
        return MaterialAdmission("mismatch", instance.consumed_identity, actual_value_identity, ("source.consumed_identity_mismatch",))
    from stratbox.core.execution.value_context import value_context
    intrinsic = value_context(prepared.value, prepared.contract)
    if intrinsic.source_ids and set(intrinsic.source_ids) != {instance.source_id}:
        return MaterialAdmission("mismatch", instance.material_identity, reasons=("source.resolved_source_context_mismatch",))
    for use in intrinsic.uses:
        if use.coordinate.source_id != instance.source_id:
            continue
        for field in ("issue_id", "asset_id", "layout_edition", "semantic_profile_edition"):
            claimed = getattr(instance, field)
            observed = getattr(use.coordinate, field)
            if claimed is not None and observed is not None and claimed != observed:
                return MaterialAdmission("mismatch", instance.material_identity, reasons=("source.resolved_" + field + "_mismatch",))
    actual_materials = {use.coordinate.material_identity for use in intrinsic.uses if use.coordinate.source_id == instance.source_id and use.coordinate.material_identity is not None}
    if instance.source_material_identity is not None and actual_materials and actual_materials != {instance.source_material_identity}:
        return MaterialAdmission("mismatch", instance.source_material_identity, reasons=("source.resolved_provenance_mismatch",))
    actual_groups = {use.coordinate.source_group_id for use in intrinsic.uses if use.coordinate.source_id == instance.source_id and use.coordinate.source_group_id}
    if instance.group_id is not None and actual_groups and actual_groups != {instance.group_id}:
        return MaterialAdmission("mismatch", instance.material_identity, reasons=("source.resolved_group_context_mismatch",))
    if material is None and isinstance(prepared.value, SourcePayload):
        material = prepared.value
    if material is None:
        # An existing typed value can be consumed without acquiring its original.
        # This verifies the exact consumed value, not availability of old bytes.
        if instance.material_identity is not None:
            return MaterialAdmission("unverified", instance.material_identity, actual_value_identity,
                                     ("source.material_reference_unresolved",))
        return MaterialAdmission("not_required", None, actual_value_identity)
    actual = ByteIdentity.of(material.data)
    if instance.material_identity is not None and actual != instance.material_identity:
        return MaterialAdmission("mismatch", instance.material_identity, actual, ("source.material_identity_mismatch",))
    if receipt is not None and getattr(receipt, "identity", None) != actual:
        return MaterialAdmission("mismatch", instance.material_identity, actual, ("source.material_receipt_mismatch",))
    return MaterialAdmission("verified", instance.material_identity, actual)


def canonical_domain_admitter(requirement, instance, value):
    """Invoke trusted admission owners referenced by the selected source group."""
    from stratbox.domains.registry.declarations import source_group, profile_document
    from stratbox.core.resources import resource_owners
    if instance.group_id is None:
        return DomainAdmission("conditional", ("source.group_unspecified",))
    group = source_group(instance.source_id, instance.group_id)
    if instance.profile_id is not None and instance.profile_id not in group.profile_ids:
        return DomainAdmission("rejected", ("source.profile_mismatch",))
    profile_ids = requirement.profile_ids or ((instance.profile_id,) if instance.profile_id else group.profile_ids)
    callbacks = []
    for owner in resource_owners():
        for profile_id in profile_ids:
            try:
                declaration = profile_document(owner, profile_id)["declaration"]
            except ValueError as error:
                if str(error) != "registry.profile_unknown":
                    raise
                continue
            reference = declaration.get("admission_ref")
            if reference is not None and reference not in callbacks:
                callbacks.append(reference)
    if not callbacks:
        return DomainAdmission("unassessed", ("source.domain_admitter_unavailable",))
    outcomes = []
    for reference in callbacks:
        module, name = reference.split(":")
        callback = import_module(module)
        for component in name.split("."):
            callback = getattr(callback, component)
        if not callable(callback):
            raise ValueError("source.domain_admitter_invalid")
        result = callback(requirement, instance, value)
        if not isinstance(result, DomainAdmission):
            raise ValueError("source.domain_admitter_result_invalid")
        outcomes.append(result)
    rejected = [outcome for outcome in outcomes if outcome.state == "rejected"]
    if rejected:
        return DomainAdmission("rejected", tuple(dict.fromkeys(reason for outcome in rejected for reason in outcome.reasons)))
    admitted = [outcome for outcome in outcomes if outcome.state == "admitted"]
    if admitted:
        return DomainAdmission("admitted", tuple(dict.fromkeys(reason for outcome in admitted for reason in outcome.reasons)))
    return DomainAdmission("conditional", tuple(dict.fromkeys(reason for outcome in outcomes for reason in outcome.reasons)))


def _domain_check(callback, requirement, instance, prepared):
    if callback is None or prepared is None:
        return DomainAdmission("unassessed")
    result = callback(requirement, instance, prepared.value)
    if not isinstance(result, DomainAdmission):
        raise ValueError("source.domain_admitter_result_invalid")
    return result


def _supplied(requirement, value):
    if value is None:
        return ()
    return value if isinstance(value, tuple) else (value,)


def assess_requirements(operation_id, requirements, available, *, report_date=None, publication_step=None, perimeter=None,
                        resolver=None, domain_admitter=None, environment="not_checked", effects="not_checked"):
    """Keep declaration claims, actual materials and domain admission separate."""
    if not isinstance(available, Mapping):
        raise ValueError("registry.source_instances_invalid")
    if environment not in {"not_checked", "available", "unavailable"} or effects not in {"not_checked", "authorized", "unavailable", "not_required"}:
        raise ValueError("source.runtime_admission_invalid")
    if report_date is not None:
        date.fromisoformat(report_date)
    if publication_step is not None and (isinstance(publication_step, bool) or not isinstance(publication_step, (int, float)) or not isfinite(publication_step) or publication_step <= 0):
        raise ValueError("registry.source_instance_step_invalid")
    expected = {"report_date": report_date, "publication_step": publication_step, "perimeter": perimeter}
    resolved = {requirement.input_name: tuple(_actual_resolution(requirement, item, resolver) for item in _supplied(requirement, available.get(requirement.input_name))) for requirement in requirements}
    coordinates = {name: set() for name in _COMPATIBILITY_FIELDS}
    for requirement in requirements:
        for instance, *_ in resolved[requirement.input_name]:
            for name in requirement.compatibility:
                if (value := getattr(instance, name)) is not None:
                    coordinates[name].add(value)
    assessments = []
    for requirement in requirements:
        values = resolved[requirement.input_name]
        instances = tuple(item[0] for item in values)
        if not values:
            assessments.append(RequirementAssessment(requirement, (), "missing" if requirement.required else "optional_missing",
                ("source.required_missing",) if requirement.required else (),
                ReadinessLayers(instances="missing", structure="unverified", material="unverified", domain="unassessed")))
            continue
        reasons, unqualified, materials, domains = [], [], [], []
        if len(instances) < requirement.minimum or requirement.maximum is not None and len(instances) > requirement.maximum:
            reasons.append("source.cardinality_mismatch")
        for instance, prepared, material, receipt in values:
            if instance.source_id not in requirement.source_ids:
                reasons.append("source.identity_mismatch")
            if instance.contract not in requirement.accepted_contracts:
                reasons.append("source.contract_mismatch")
            if requirement.group_id is not None:
                if instance.group_id is None:
                    unqualified.append("source.group_unspecified")
                elif instance.group_id != requirement.group_id:
                    reasons.append("source.group_mismatch")
            if requirement.profile_ids:
                if instance.profile_id is None:unqualified.append("source.profile_unspecified")
                elif instance.profile_id not in requirement.profile_ids:reasons.append("source.profile_mismatch")
            if requirement.grain:
                if not instance.grain:unqualified.append("source.grain_unspecified")
                elif instance.grain != requirement.grain:reasons.append("source.grain_mismatch")
            for field, allowed in (("layout_edition", requirement.layout_editions), ("semantic_profile_edition", requirement.semantic_profile_editions)):
                if allowed:
                    if getattr(instance, field) is None:unqualified.append("source." + field + "_unspecified")
                    elif getattr(instance, field) not in allowed:reasons.append("source." + field + "_mismatch")
            for name in requirement.compatibility:
                value = getattr(instance, name)
                if value is None:unqualified.append("source." + name + "_unspecified")
                elif expected[name] is not None and value != expected[name] or len(coordinates[name]) > 1:reasons.append("source." + name + "_mismatch")
            admission = _material_admission(instance, prepared, material, receipt)
            materials.append(admission)
            if admission.state in {"mismatch", "inaccessible"}:reasons.extend(admission.reasons)
            elif admission.state == "unverified":unqualified.extend(admission.reasons)
            domain = _domain_check(domain_admitter, requirement, instance, prepared) if not reasons else DomainAdmission("unassessed")
            domains.append(domain.state)
            if domain.state == "rejected":reasons.extend(domain.reasons or ("source.domain_rejected",))
            elif domain.state in {"conditional", "unassessed"}:unqualified.extend(domain.reasons or ("source.domain_" + domain.state,))
        reasons, unqualified = tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(unqualified))
        state = "incompatible" if reasons else "unqualified" if unqualified else "admitted"
        material_states = {item.state for item in materials}
        structural_failures = {"source.contract_mismatch", "source.resolved_contract_mismatch", "source.material_value_type_mismatch", "source.prepared_identity_mismatch", "source.consumed_identity_mismatch"}
        applicability_failures = {"source.identity_mismatch", "source.group_mismatch", "source.profile_mismatch", "source.grain_mismatch", "source.layout_edition_mismatch", "source.semantic_profile_edition_mismatch"}
        layers = ReadinessLayers(
            applicability="inapplicable" if set(reasons) & applicability_failures else "supported",
            structure="incompatible" if set(reasons) & structural_failures else "valid" if all(item[1] is not None for item in values) else "unverified",
            material=next(iter(material_states)) if len(material_states) == 1 else "mixed",
            domain=domains[0] if len(set(domains)) == 1 else "mixed", environment=environment, effects=effects)
        assessments.append(RequirementAssessment(requirement, instances, state, reasons + unqualified, layers, tuple(materials)))
    return OperationReadiness(operation_id, tuple(assessments), tuple(sorted(set(available) - {item.input_name for item in requirements})), environment, effects)


def operation_readiness(catalog, operation_id, available, *, environment_check=None, effect_check=None, **context):
    definition = catalog.metadata(operation_id)
    if context.get("domain_admitter") is None:
        context["domain_admitter"] = canonical_domain_admitter
    environment = environment_check(definition) if environment_check else "not_checked"
    effects = effect_check(definition) if effect_check else "not_required" if not definition.possible_effects else "not_checked"
    return assess_requirements(operation_id, operation_requirements(catalog, operation_id), available, environment=environment, effects=effects, **context)


def validate_source_assembly(value, *, owner_id=None):
    """Validate declarative role-to-field assembly without importing its type."""
    if not isinstance(value, dict):
        raise ValueError("registry.source_assembly_invalid")
    for port, assembly in value.items():
        safe_token(port)
        if not isinstance(assembly, dict) or not {"type_ref", "fields"} <= set(assembly) or set(assembly) - {"type_ref", "fields", "context_parameters"}:
            raise ValueError("registry.source_assembly_invalid")
        ref = assembly["type_ref"]
        if not isinstance(ref, str) or ref.count(":") != 1:
            raise ValueError("registry.source_assembly_invalid")
        module, symbol = ref.split(":")
        if not all(part.isidentifier() for part in (*module.split("."), *symbol.split("."))):
            raise ValueError("registry.source_assembly_invalid")
        if owner_id is not None:
            boundary = "stratbox.core" if owner_id.startswith("core.") else "stratbox.domains." + owner_id
            if not (module == boundary or module.startswith(boundary + ".")):
                raise ValueError("registry.source_assembly_owner_mismatch")
        mapping = assembly["fields"]
        if not isinstance(mapping, dict) or not mapping or len(set(mapping.values())) != len(mapping):
            raise ValueError("registry.source_assembly_fields_invalid")
        for role, target in mapping.items():
            safe_token(role)
            if not isinstance(target, str) or not target.isidentifier():
                raise ValueError("registry.source_assembly_fields_invalid")
        context_parameters = assembly.get("context_parameters", {})
        if not isinstance(context_parameters, dict) or not set(context_parameters) <= _COMPATIBILITY_FIELDS:
            raise ValueError("registry.source_assembly_context_invalid")
        for path in context_parameters.values():
            if not isinstance(path, str) or not all(component.isidentifier() for component in path.split(".")):
                raise ValueError("registry.source_assembly_context_invalid")
    return value


def _assembly_types(catalog, operation_id, requirements):
    from stratbox.operations.declarations import operation_document
    document = operation_document(operation_id)
    assemblies = validate_source_assembly(document.get("source_assembly", {}), owner_id=document["owner_id"])
    definition = catalog.get(operation_id)
    port_definitions = {port.name: port for port in definition.processing.inputs} if definition.processing else {}
    request_hints = get_type_hints(definition.request_type)
    decoded = {}
    for port_name, assembly in assemblies.items():
        if port_name not in port_definitions:
            raise ValueError("registry.source_assembly_port_unknown")
        port = port_definitions[port_name]
        module, symbol = assembly["type_ref"].split(":")
        kind = import_module(module)
        for part in symbol.split("."):
            kind = getattr(kind, part)
        if not isinstance(kind, type) or not is_dataclass(kind):
            raise ValueError("registry.source_assembly_type_invalid")
        container = definition.request_type
        target = None
        for component in (port.path or port.name).split("."):
            target = get_type_hints(container).get(component)
            options = tuple(option for option in get_args(target) if option is not type(None))
            container = options[0] if len(options) == 1 else target
            if container is None:
                raise ValueError("registry.source_assembly_request_mismatch")
        if container is not kind:
            raise ValueError("registry.source_assembly_request_mismatch")
        actual_fields = {field.name for field in fields(kind)}
        roles = {requirement.input_name for requirement in requirements if requirement.port == port_name}
        if set(assembly["fields"]) != roles or not set(assembly["fields"].values()) <= actual_fields:
            raise ValueError("registry.source_assembly_roles_mismatch")
        from dataclasses import MISSING
        required_fields = {field.name for field in fields(kind) if field.default is MISSING and field.default_factory is MISSING}
        if not required_fields <= set(assembly["fields"].values()):
            raise ValueError("registry.source_assembly_fields_missing")
        for path in assembly.get("context_parameters", {}).values():
            parts = path.split(".")
            if parts[0] not in definition.processing.parameters:
                raise ValueError("registry.source_assembly_context_parameter_unknown")
            target = definition.request_type
            for component in parts:
                target = get_type_hints(target).get(component)
                if target is None:
                    raise ValueError("registry.source_assembly_context_parameter_unknown")
        decoded[port_name] = kind, assembly["fields"], get_type_hints(kind)
    for requirement in requirements:
        if requirement.port not in decoded:
            port = port_definitions[requirement.port]
            siblings = [item for item in requirements if item.port == requirement.port]
            if len(siblings) != 1 or not set(requirement.accepted_contracts) <= {port.contract, *port.alternatives}:
                raise ValueError("registry.source_assembly_required")
    return decoded


def validate_requirement_links(catalog, operation_id):
    requirements = operation_requirements(catalog, operation_id)
    if requirements:
        _assembly_types(catalog, operation_id, requirements)
    return len(requirements)


def _accepts(annotation, value):
    from types import UnionType
    from typing import Any, Union
    if annotation is Any:
        return True
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (UnionType, Union):
        return any(_accepts(arg, value) for arg in args)
    if origin is tuple:
        if not isinstance(value, tuple):return False
        return all(_accepts(args[0], item) for item in value) if args and args[-1] is Ellipsis else len(args) == len(value) and all(_accepts(kind, item) for kind, item in zip(args, value))
    return isinstance(value, annotation) if isinstance(annotation, type) else False


def bind_requirement_inputs(catalog, operation_id, available, *, resolver=None, domain_admitter=None, parameters=None):
    """Resolve named roles into the actual dataclass expected by the input port.

    Metadata-only instances cannot be bound. Material hashes and typed-value
    identities are checked against the consumed object before request assembly.
    """
    from stratbox.core.execution.handoff import PreparedInput, prepare_input
    requirements = operation_requirements(catalog, operation_id)
    assemblies = _assembly_types(catalog, operation_id, requirements)
    role_names = {requirement.input_name for requirement in requirements}
    if not isinstance(available, Mapping) or not set(available) <= role_names:
        raise ValueError("source.requirement_role_unknown")
    values, receipts, qualifications, coverage = {}, {}, {}, {}
    resolved_inputs = {}
    for requirement in requirements:
        members = []
        for incoming in _supplied(requirement, available.get(requirement.input_name)):
            instance, prepared, material, receipt = _actual_resolution(requirement, incoming, resolver)
            if prepared is None:
                raise ValueError("source.material_unresolved")
            material_admission = _material_admission(instance, prepared, material, receipt)
            if material_admission.state not in {"verified", "not_required"}:
                raise ValueError(material_admission.reasons[0] if material_admission.reasons else "source.material_unverified")
            resolved_inputs.setdefault(requirement.input_name, []).append(ResolvedSourceInstance(instance, prepared, material, receipt))
            members.append(prepared)
        if len(members) < requirement.minimum or requirement.maximum is not None and len(members) > requirement.maximum:
            raise ValueError("source.required_missing" if not members and requirement.required else "source.cardinality_mismatch")
        if not members:
            if requirement.required:raise ValueError("source.required_missing")
            values[requirement.input_name] = None if requirement.maximum == 1 else ()
        else:
            values[requirement.input_name] = tuple(member.value for member in members) if requirement.maximum != 1 else members[0].value
        receipts[requirement.input_name] = tuple(dict.fromkeys(item for member in members for item in member.used_inputs))
        qualifications[requirement.input_name] = frozenset.intersection(*(member.qualifications for member in members)) if members else frozenset()
        coverage[requirement.input_name] = frozenset.intersection(*(member.coverage for member in members)) if members else frozenset()
    domain_admitter = domain_admitter or canonical_domain_admitter
    from stratbox.operations.declarations import operation_document
    expected_coordinates = {}
    for assembly in operation_document(operation_id).get("source_assembly", {}).values():
        for name, path in assembly.get("context_parameters", {}).items():
            parts = path.split(".")
            if parameters is None or parts[0] not in parameters:
                continue
            coordinate = parameters[parts[0]]
            for component in parts[1:]:
                if not is_dataclass(coordinate) or component not in {field.name for field in fields(coordinate)}:
                    raise ValueError("source.context_parameter_invalid")
                coordinate = getattr(coordinate, component)
            if name in expected_coordinates and expected_coordinates[name] != coordinate:
                raise ValueError("source.context_parameter_conflict")
            expected_coordinates[name] = coordinate
    readiness = assess_requirements(operation_id, requirements, {name: tuple(items) for name, items in resolved_inputs.items()}, domain_admitter=domain_admitter, **expected_coordinates)
    if readiness.state == "blocked" or any(reason in {"source.group_unspecified", "source.profile_unspecified", "source.grain_unspecified", "source.layout_edition_unspecified", "source.semantic_profile_edition_unspecified"} for item in readiness.requirements for reason in item.reasons):
        first = next((item for item in readiness.requirements if item.state in {"missing", "incompatible", "rejected", "unqualified"}), None)
        raise ValueError(first.reasons[0] if first and first.reasons else "source.requirements_rejected")
    definition = catalog.get(operation_id)
    ports = {port.name: port for port in definition.processing.inputs}
    result = {}
    for port_name in {requirement.port for requirement in requirements}:
        participating = [requirement for requirement in requirements if requirement.port == port_name]
        if port_name in assemblies:
            kind, mapping, hints = assemblies[port_name]
            constructor = {mapping[requirement.input_name]: values[requirement.input_name] for requirement in participating}
            for name, value in constructor.items():
                if name not in hints or not _accepts(hints[name], value):
                    raise ValueError("source.assembly_value_type_mismatch")
            value = kind(**constructor)
        else:
            value = values[participating[0].input_name]
        evidence = tuple(dict.fromkeys(item for requirement in participating for item in receipts[requirement.input_name]))
        present = [requirement for requirement in participating if values[requirement.input_name] is not None and values[requirement.input_name] != ()]
        common_qualifications = frozenset.intersection(*(qualifications[requirement.input_name] for requirement in present)) if present else frozenset()
        common_coverage = frozenset.intersection(*(coverage[requirement.input_name] for requirement in present)) if present else frozenset()
        from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, ValueContext
        from stratbox.domains.registry.declarations import source_cards
        from stratbox.core.resources import resource_owners
        families = {card.series_id: card.family_id for owner in resource_owners() for card in source_cards(owner)}
        uses = []
        for requirement in participating:
            for resolved in resolved_inputs.get(requirement.input_name, ()):
                instance = resolved.instance
                material = _material_admission(instance, resolved.value, resolved.material, resolved.receipt)
                from stratbox.core.execution.value_context import value_context
                actual_context = getattr(resolved.value, "source_context", None) or value_context(resolved.value.value, resolved.value.contract)
                actual_uses = tuple(use for use in actual_context.uses if use.coordinate.source_id == instance.source_id)
                if actual_uses:
                    # The retained container is delivery evidence. Preserve the
                    # source material and qualification of the actual datum.
                    uses.extend(replace(use, input_role=requirement.input_name) for use in actual_uses)
                    continue
                identity = instance.source_material_identity or (material.actual_identity if material.state == "verified" else None)
                coordinate = SourceCoordinate(instance.source_id, families.get(instance.source_id), instance.group_id,
                    instance.issue_id, instance.asset_id, identity, instance.layout_edition, instance.semantic_profile_edition)
                uses.append(SourceUse(coordinate, requirement.input_name,
                    "material_verified" if material.state == "verified" else "value_verified",
                    getattr(getattr(resolved.receipt, "identity", None), "sha256", None)))
        prepared = prepare_input(value, ports[port_name].contract, receipts=evidence,
            qualifications=common_qualifications, coverage=common_coverage, source_context=ValueContext(tuple(uses)))
        computations = []
        for requirement in participating:
            members = resolved_inputs.get(requirement.input_name, ())
            for position, resolved in enumerate(members):
                label = requirement.input_name if len(members) == 1 else f"{requirement.input_name}.{position}"
                member = resolved.value
                if member.computation is not None:
                    computations.append((label, member.computation))
                computations.extend((f"{label}.{name}", receipt) for name, receipt in getattr(member, "member_computations", ()))
        result[port_name] = replace(prepared, member_computations=tuple(computations))

    return result
