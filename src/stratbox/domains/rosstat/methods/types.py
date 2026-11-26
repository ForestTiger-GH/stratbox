"""Exact source values and evidence from reviewed Rosstat table layouts."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Literal
from stratbox.shared.data.values import Assessment, SourceDataset, TableEvidenceSet, WorkbookEvidence, fingerprint
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.workbook_cells import SheetCells
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.coverage import SnapshotCoverage

@dataclass(frozen=True, slots=True)
class SourceValue:
    indicator_id: str
    label: str
    measure: str
    frequency: str
    period_start: date
    period_end: date
    display_date: date
    value: Decimal | None
    value_status: str
    raw_token: str | None
    unit_literal: str
    unit: str | None
    scale: Decimal
    quantity_kind: str | None
    geography_namespace: str
    geography_id: str
    source_locator: str
    source_sheet: str = ""
    source_row: int = 0
    source_column: int = 0
    footnotes: tuple[str, ...] = ()
    dimensions: tuple[tuple[str, str], ...] = ()
    perimeter: str = "publisher_defined"
    period_kind: str = "interval"
    source_kind: str = ""
    number_format: str = "General"
    formula: str | None = None
    source_year_literal: str = ""
    period_label_literal: str = ""

    def __post_init__(self):
        if not all((self.indicator_id, self.label, self.measure, self.frequency, self.source_locator,
                    self.geography_namespace, self.geography_id, self.perimeter)):
            raise ValueError("rosstat.value_identity_required")
        if self.period_start > self.period_end or self.period_kind not in {"interval", "as_of"}:
            raise ValueError("rosstat.value_period_invalid")
        if self.period_kind == "as_of" and self.period_start != self.period_end:
            raise ValueError("rosstat.value_period_invalid")
        if self.value_status not in {"reported", "blank", "dash", "missing", "not_applicable", "withheld", "unparsed"}:
            raise ValueError("rosstat.value_status_invalid")
        if (self.value_status == "reported") != (self.value is not None):
            raise ValueError("rosstat.value_status_mismatch")
        if self.value is not None and (not isinstance(self.value, Decimal) or not self.value.is_finite()):
            raise ValueError("rosstat.value_invalid")
        if not isinstance(self.scale, Decimal) or not self.scale.is_finite() or self.scale <= 0:
            raise ValueError("rosstat.value_scale_invalid")
        if self.quantity_kind not in {None, "stock", "flow", "ratio", "index", "count"}:
            raise ValueError("rosstat.value_quantity_invalid")
        if len(dict(self.dimensions)) != len(self.dimensions):
            raise ValueError("rosstat.value_dimensions_invalid")

    @property
    def key(self) -> tuple:
        return (self.indicator_id, self.measure, self.frequency, self.period_kind,
                self.period_start, self.period_end, self.geography_namespace,
                self.geography_id, self.perimeter, tuple(sorted(self.dimensions)))


@dataclass(frozen=True, slots=True)
class RowDecision:
    """Every candidate row remains traceable when the notebook's last-row policy applies."""
    indicator_id: str
    measure: str
    sheet: str
    row: int
    year: int
    selected: bool
    reason: str
    # Canonical source-cell evidence for A:R, including rejected candidate rows.
    source_cells: str


@dataclass(frozen=True, slots=True)
class SectionEvidence:
    indicator_id: str
    measure: str
    sheet: str
    title_row: int
    marker_row: int | None
    start_row: int
    end_row: int
    source_title: str
    headers: tuple[str, ...]
    unit_literal: str
    notes: tuple[str, ...]



@dataclass(frozen=True, slots=True)
class SourceTable:
    series_id: str
    issue_id: str
    asset_id: str
    source_identity: ByteIdentity
    physical_identity: ByteIdentity
    rules_id: str
    values: tuple[SourceValue, ...]
    sections: tuple[SectionEvidence, ...]
    row_decisions: tuple[RowDecision, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.series_id.startswith("rosstat.") or not self.issue_id or not self.asset_id or not self.rules_id:
            raise ValueError("rosstat.table_identity_invalid")
        if not self.values or len({item.key for item in self.values}) != len(self.values):
            raise ValueError("rosstat.table_values_invalid")
        if not any(item.identity == self.source_identity for item in self.lineage):
            raise ValueError("rosstat.table_source_evidence_required")

    @property
    def identity(self):
        return ByteIdentity.of(canonical_manifest_bytes(asdict(self)))

@dataclass(frozen=True, slots=True)
class Kep2Settings:
    workbook: object
    duplicate_year_policy: Literal["last_source_row", "reject"] = "last_source_row"
    required_indicators: tuple[str, ...] = ()
    title_aliases: tuple[tuple[str, str], ...] = ()
    unit_overrides: tuple[tuple[str, str, str, Decimal], ...] = ()

@dataclass(frozen=True, slots=True)
class TableRules:
    source_id: str
    publication_id: str
    kind: str
    required_indicators: tuple[str, ...] = ()
    selected_rows: tuple[int, ...] = ()
    selected_years: tuple[int, ...] = ()
    duplicate_year_policy: str = "last_source_row"

@dataclass(frozen=True, slots=True)
class BoundWorkbook:
    series_id: str
    issue_id: str
    asset_id: str
    source_identity: ByteIdentity
    identity: ByteIdentity
    sheets: tuple[SheetCells, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage
    format: str = "xlsx"


def bind_workbook(tables, rules: TableRules, parameters=None):
    if not isinstance(tables, TableEvidenceSet) or len(tables.tables) != 1:
        raise ValueError("rosstat.physical_workbook_required")
    if tables.source_id not in {rules.source_id, rules.publication_id, None}:
        raise ValueError("rosstat.source_context_conflict")
    physical = tables.tables[0]
    if isinstance(physical, WorkbookEvidence):
        material, workbook = physical.material, physical.workbook
    else:
        material, workbook = tables.material, physical
    if material is None or not hasattr(workbook, "sheets"):
        raise ValueError("rosstat.material_evidence_required")
    if workbook.identity != material.identity:
        raise ValueError("rosstat.physical_material_identity_conflict")
    if material.source_id not in {None, rules.source_id, rules.publication_id}:
        raise ValueError("rosstat.source_context_conflict")
    issue = tables.issue_id or str((parameters or {}).get("issue_id", material.metadata.get("issue_id", "")))
    if not issue:
        raise ValueError("rosstat.issue_required")
    lineage = tuple(item for item in material.lineage if isinstance(item, UsedInputReceipt))
    if not any(item.identity == material.identity for item in lineage):
        lineage += (UsedInputReceipt("publisher_material", material.identity, material.media_type, "inline", rules.publication_id),)
    return BoundWorkbook(rules.publication_id, issue, str(material.metadata.get("asset_id", "main")),
        material.identity, workbook.identity, workbook.sheets, lineage,
        SnapshotCoverage(tables.assessment.status, "Exactly the supplied physical workbook evidence."),
        str(material.metadata.get("format", "xlsx")))


def as_dataset(table: SourceTable, *, source_id=None):
    rows = []
    for value in table.values:
        row = asdict(value)
        row.update(metric=value.indicator_id + "." + value.measure, subject=value.geography_id,
            period=value.period_start.isoformat() if value.period_kind == "as_of" else (value.period_start.isoformat(), value.period_end.isoformat()),
            subject_namespace=value.geography_namespace, measure_kind=value.quantity_kind,
            evidence_ref=table.source_identity.sha256 + "#" + value.source_locator,
            source_id=source_id or table.series_id, issue_id=table.issue_id)
        rows.append(row)
    return SourceDataset(source_id or table.series_id, tuple(rows),
        {"grain": ("metric", "geography_namespace", "subject", "frequency", "period", "perimeter"),
         "rules_id": table.rules_id, "source_table_identity": table.identity.sha256,
         "sections": tuple(asdict(item) for item in table.sections),
         "row_decisions": tuple(asdict(item) for item in table.row_decisions)},
        table.issue_id, table.lineage,
        Assessment(table.coverage.status, table.diagnostics, qualifications=frozenset({"source_native_geography", "reported_values"})),
        source_uses=(SourceUse(SourceCoordinate(source_id=source_id or table.series_id,
            family_id=table.series_id, source_group_id=table.rules_id, issue_id=table.issue_id,
            asset_id=table.asset_id, material_identity=table.source_identity,
            layout_identity=fingerprint((table.rules_id, tuple(asdict(item) for item in table.sections))),
            semantic_identity=fingerprint(tuple((item.indicator_id, item.measure, item.frequency,
                item.period_kind, item.period_start, item.period_end, item.unit, item.scale,
                item.quantity_kind, item.geography_namespace, item.perimeter, item.dimensions)
                for item in table.values))),
            "table_interpretation", "domain_validated", "sha256:" + table.source_identity.sha256),))
