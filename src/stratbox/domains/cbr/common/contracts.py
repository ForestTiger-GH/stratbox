"""Narrow immutable settings for one standard action; no executable catalog."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import date


@dataclass(frozen=True, slots=True)
class Publication:
    series_id: str
    family_id: str
    title: str
    issue_model: str
    formats: tuple[str, ...]
    kind: str
    locator: str
    filename_pattern: str | None = None


@dataclass(frozen=True, slots=True)
class Semantics:
    period_model: str
    grain: tuple[str, ...]
    scope: str


@dataclass(frozen=True, slots=True)
class TableVariant:
    variant_id: str
    sheet_pattern: str
    role: str
    quantity_kind: str | None
    period_basis: str
    dimensions: tuple[str, ...]
    unit_policy: str
    qualification: str
    unit_anchor: str | None = None


@dataclass(frozen=True, slots=True)
class CorporateMeaning:
    publisher_code: str
    layout: str
    row_dimension: str
    quantity_kind: str
    portfolio_scope: str


@dataclass(frozen=True, slots=True)
class StatisticalSettings:
    series_id: str
    variants: tuple[TableVariant, ...]
    source_kind: str = "workbook"
    strict: bool = False
    corporate: CorporateMeaning | None = None


@dataclass(frozen=True, slots=True)
class FormSettings:
    series_id: str
    code: str
    numeric_fields: tuple[str, ...] = ()
    row_fields: tuple[str, ...] = ()
    subject_field: str = "REGN"
    quantity_kind: str = "stock"
    unit: str = "RUB"
    scale: Decimal = Decimal(1000)
    required_fields: tuple[tuple[str, str, int], ...] = ()
    require_measurement: bool = False


@dataclass(frozen=True, slots=True)
class FamilySettings:
    series_id: str
    kind: str


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    series_id: str
    formats: tuple[str, ...]
    issue_required: bool = False


@dataclass(frozen=True, slots=True)
class SourceContentEvidence:
    output: object
    inputs: tuple[object, ...]
    context_identity: str | None = None


@dataclass(frozen=True, slots=True)
class SubjectBinding:
    source_namespace: str
    source_id: str
    target_namespace: str
    target_id: str
    reference_identity: str
    valid_from: date | None = None
    valid_until: date | None = None


@dataclass(frozen=True, slots=True)
class MappingRules:
    series_id: str
    subjects: tuple[tuple[str, str, str], ...] = ()
    metrics: tuple[tuple[str, str], ...] = ()
    require_all: bool = False
    bindings: tuple[SubjectBinding, ...] = ()
