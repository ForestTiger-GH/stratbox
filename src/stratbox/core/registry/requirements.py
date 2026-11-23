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
from typing import Mapping

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
        for identity in self.source_ids:
            safe_token(identity)


@dataclass(frozen=True, slots=True)
class SourceInstance:
    """A selected publication/material, independently of transport or storage."""

    source_id: str
    contract: DataContract
    group_id: str | None = None
    report_date: str | None = None
    publication_step: float | None = None
    perimeter: str | None = None
    issue_id: str | None = None
    material_identity: ByteIdentity | None = None
    revision: str | None = None

    def __post_init__(self):
        safe_token(self.source_id)
        if not isinstance(self.contract, DataContract):
            raise ValueError("registry.source_instance_invalid")
        for token in (self.group_id, self.perimeter, self.issue_id, self.revision):
            if token is not None:
                safe_token(token)
        if self.report_date is not None:
            try:
                date.fromisoformat(self.report_date)
            except (TypeError, ValueError):
                raise ValueError("registry.source_instance_date_invalid") from None
        if self.publication_step is not None and (
                isinstance(self.publication_step, bool) or not isinstance(self.publication_step, (int, float))
                or not isfinite(self.publication_step) or self.publication_step <= 0):
            raise ValueError("registry.source_instance_step_invalid")
        if self.material_identity is not None and not isinstance(self.material_identity, ByteIdentity):
            raise ValueError("registry.source_instance_identity_invalid")


@dataclass(frozen=True, slots=True)
class RequirementAssessment:
    requirement: SourceRequirement
    instances: tuple[SourceInstance, ...]
    state: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationReadiness:
    operation_id: str
    requirements: tuple[RequirementAssessment, ...]
    unexpected_inputs: tuple[str, ...] = ()

    @property
    def required_count(self):
        return sum(item.requirement.required for item in self.requirements)

    @property
    def ready_count(self):
        return sum(item.requirement.required and item.state == "ready" for item in self.requirements)

    @property
    def state(self):
        if self.unexpected_inputs or any(item.state in {"missing", "incompatible"} for item in self.requirements):
            return "blocked"
        if any(item.state == "unqualified" for item in self.requirements):
            return "conditional"
        return "ready"


def decode_requirement(value):
    required = {"input_name", "source_ids", "accepted_contracts", "role", "port"}
    optional = {"group_id", "required", "minimum", "maximum", "compatibility", "source_label"}
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
    if options.get("required") is False and "minimum" not in options:
        options["minimum"] = 0
    return SourceRequirement(**options)


@lru_cache(maxsize=4096)
def declared_requirements(operation_id):
    """Decode dependency facts without importing an operation implementation."""
    from stratbox.core.registry.operations import operation_document
    values = operation_document(operation_id).get("source_requirements", [])
    if not isinstance(values, list):
        raise ValueError("registry.source_requirements_invalid")
    requirements = tuple(decode_requirement(value) for value in values)
    if len({item.input_name for item in requirements}) != len(requirements):
        raise ValueError("registry.source_requirement_duplicate")
    return requirements


def operation_requirements(catalog, operation_id):
    """Resolve declared roles against registered ports and canonical sources."""
    operation = catalog.get(operation_id)
    if catalog.reference(operation_id).definition is not None:
        return ()
    requirements = declared_requirements(operation_id)
    if not requirements:
        return ()
    from stratbox.core.registry.sources import source_documents
    sources = {source["series_id"] for owner in {item.owner_id for item in catalog.registrations}
               for source in source_documents(owner)}
    ports = {port.name for port in operation.processing.inputs} if operation.processing else set()
    for requirement in requirements:
        if requirement.port not in ports:
            raise ValueError("registry.source_requirement_port_unknown")
        if not set(requirement.source_ids) <= sources:
            raise ValueError("registry.source_requirement_source_unknown")
    return requirements


def describe_source_requirements(catalog, operation_id):
    return tuple(asdict(item) for item in operation_requirements(catalog, operation_id))


def assess_requirements(operation_id, requirements, available, *, report_date=None, publication_step=None, perimeter=None):
    """Compare exact supplied instances and shared economic coordinates.

    Missing compatibility evidence yields a conditional result. A conflict yields
    an incompatible result, even for an optional role supplied by the caller.
    """
    if not isinstance(available, Mapping):
        raise ValueError("registry.source_instances_invalid")
    if report_date is not None:
        date.fromisoformat(report_date)
    if publication_step is not None and (isinstance(publication_step, bool)
            or not isinstance(publication_step, (int, float)) or not isfinite(publication_step) or publication_step <= 0):
        raise ValueError("registry.source_instance_step_invalid")
    expected = {"report_date": report_date, "publication_step": publication_step, "perimeter": perimeter}
    supplied = {}
    for key, value in available.items():
        instances = () if value is None else (value,) if isinstance(value, SourceInstance) else value
        if not isinstance(instances, tuple) or any(not isinstance(item, SourceInstance) for item in instances):
            raise ValueError("registry.source_instances_invalid")
        supplied[key] = instances
    coordinates = {name: set() for name in _COMPATIBILITY_FIELDS}
    for requirement in requirements:
        for instance in supplied.get(requirement.input_name, ()):
            for name in requirement.compatibility:
                value = getattr(instance, name)
                if value is not None:
                    coordinates[name].add(value)
    assessments = []
    for requirement in requirements:
        instances = supplied.get(requirement.input_name, ())
        if not instances:
            assessments.append(RequirementAssessment(requirement, (), "missing" if requirement.required else "optional_missing",
                ("source.required_missing",) if requirement.required else ()))
            continue
        reasons, unqualified = [], []
        if len(instances) < requirement.minimum or requirement.maximum is not None and len(instances) > requirement.maximum:
            reasons.append("source.cardinality_mismatch")
        for instance in instances:
            if instance.source_id not in requirement.source_ids:
                reasons.append("source.identity_mismatch")
            if instance.contract not in requirement.accepted_contracts:
                reasons.append("source.contract_mismatch")
            if requirement.group_id is not None:
                if instance.group_id is None:
                    unqualified.append("source.group_unspecified")
                elif instance.group_id != requirement.group_id:
                    reasons.append("source.group_mismatch")
            if instance.material_identity is None:
                unqualified.append("source.material_unresolved")
            for name in requirement.compatibility:
                value = getattr(instance, name)
                if value is None:
                    unqualified.append("source." + name + "_unspecified")
                elif expected[name] is not None and value != expected[name] or len(coordinates[name]) > 1:
                    reasons.append("source." + name + "_mismatch")
        reasons = tuple(dict.fromkeys(reasons))
        unqualified = tuple(dict.fromkeys(unqualified))
        state = "incompatible" if reasons else "unqualified" if unqualified else "ready"
        assessments.append(RequirementAssessment(requirement, instances, state, reasons + unqualified))
    return OperationReadiness(operation_id, tuple(assessments), tuple(sorted(set(available) - {item.input_name for item in requirements})))


def operation_readiness(catalog, operation_id, available, **context):
    return assess_requirements(operation_id, operation_requirements(catalog, operation_id), available, **context)
