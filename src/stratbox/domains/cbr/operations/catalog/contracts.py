"""Source and family descriptions expose exact scoped processing contracts."""
from __future__ import annotations
from dataclasses import dataclass
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationKey, ProcessingStage
from stratbox.shared.data.processing import DataContract
from stratbox.domains.cbr.publications.contracts import SourceSeries
from stratbox.domains.cbr.tables.statistics.contracts import SourceTableProfile


@dataclass(frozen=True, slots=True)
class DescribeSourceRequest:
    series_id: str
    format: str | None = None
    table_id: str | None = None
    edition: str | None = None


@dataclass(frozen=True, slots=True)
class DescribeFamilyRequest:
    family_id: str


@dataclass(frozen=True, slots=True)
class BoundOperation:
    key: OperationKey
    method_version: str
    stages: tuple[ProcessingStage, ...]
    inputs: tuple[InputPort, ...]
    outputs: tuple[OutputPort, ...]
    parameters: tuple[str, ...]
    summary: str
    composition: bool
    qualifications: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScopedStage:
    stage: ProcessingStage
    state: str
    operations: tuple[OperationKey, ...]
    reason: str
    qualifications: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TableDescription:
    table_id: str
    variant_id: str
    edition: str
    schema_contracts: tuple[DataContract, ...]
    source_pattern: str
    role: str
    quantity_kind: str | None
    period_basis: str
    dimensions: tuple[str, ...]
    unit_policy: str
    qualification: str
    unit_anchor: str | None = None


@dataclass(frozen=True, slots=True)
class ScopedHandoff:
    producer: OperationKey
    output: str
    consumer: OperationKey
    input: str
    assembly: str
    source_contract: DataContract
    input_contract: DataContract
    qualifications: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BoundProfile:
    profile_id: str
    kind: str
    edition: str
    operations: tuple[OperationKey, ...]
    formats: tuple[str, ...]
    scope: str


@dataclass(frozen=True, slots=True)
class SourceDescription:
    source: SourceSeries
    table_profile: SourceTableProfile
    tables: tuple[TableDescription, ...]
    operations: tuple[BoundOperation, ...]
    stages: tuple[ScopedStage, ...]
    handoffs: tuple[ScopedHandoff, ...]
    supported_formats: tuple[str, ...]
    original_only_formats: tuple[str, ...]
    selection: tuple[tuple[str, str], ...] = ()
    qualifications: tuple[str, ...] = ()
    profiles: tuple[BoundProfile, ...] = ()
    delegated_operations: tuple[BoundOperation, ...] = ()


@dataclass(frozen=True, slots=True)
class FamilyStage:
    stage: ProcessingStage
    supported_sources: tuple[str, ...]
    conditional_sources: tuple[str, ...]
    missing_sources: tuple[str, ...]
    delegated_sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MethodDependency:
    input_name: str
    series_id: str
    required: bool
    contracts: tuple[DataContract, ...]
    compatibility_rule: str


@dataclass(frozen=True, slots=True)
class MethodDescription:
    method_id: str
    operations: tuple[BoundOperation, ...]
    dependencies: tuple[MethodDependency, ...]
    qualifications: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FamilyDescription:
    family_id: str
    sources: tuple[SourceDescription, ...]
    stages: tuple[FamilyStage, ...]
    methods: tuple[MethodDescription, ...] = ()
