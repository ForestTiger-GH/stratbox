"""Source-faithful selected table flakes, distinct from full physical evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, TYPE_CHECKING

from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.shared.data.snapshots import SnapshotCoverage

if TYPE_CHECKING:
    from stratbox.shared.data.workbooks import WorkbookExtract
    from stratbox.shared.reference.geography.editions import TerritoryEdition


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
class RosstatSourceFlake:
    series_id: str
    issue_id: str
    asset_id: str
    source_identity: ByteIdentity
    physical_identity: ByteIdentity
    profile_id: str
    profile_version: int
    values: tuple[SourceValue, ...]
    sections: tuple[SectionEvidence, ...]
    row_decisions: tuple[RowDecision, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self):
        SourceAssetIdentity(self.series_id, self.issue_id, self.asset_id)
        if not self.series_id.startswith("rosstat.") or not self.profile_id or self.profile_version < 1:
            raise ValueError("rosstat.flake_identity_invalid")
        if len({item.key for item in self.values}) != len(self.values):
            raise ValueError("rosstat.flake_duplicate_observation")
        if not self.values:
            raise ValueError("rosstat.flake_empty")
        if not self.lineage or not any(item.identity == self.source_identity for item in self.lineage):
            raise ValueError("rosstat.flake_source_lineage_required")

    @property
    def identity(self) -> ByteIdentity:
        from .snapshots import flake_snapshot
        return flake_snapshot(self).identity


@dataclass(frozen=True, slots=True)
class Kep2Request:
    workbook: WorkbookExtract
    # The supplied notebook explicitly chooses the last source row after year forward-fill.
    duplicate_year_policy: Literal["last_source_row", "reject"] = "last_source_row"
    required_indicators: tuple[str, ...] = ()
    # Explicit reviewed source labels may extend layout spelling, never fuzzy matching.
    title_aliases: tuple[tuple[str, str], ...] = ()
    unit_overrides: tuple[tuple[str, str, str, Decimal], ...] = ()


@dataclass(frozen=True, slots=True)
class CellBinding:
    """A reviewed source coordinate with explicit statistical semantics."""
    source_locator: str
    indicator_id: str
    label: str
    unit: str
    unit_literal: str
    quantity_kind: str
    frequency: str
    period_start: date
    period_end: date
    geography_namespace: str
    geography_id: str
    measure: str = "absolute"
    scale: Decimal = Decimal(1)
    period_kind: str = "interval"
    display_date: date | None = None
    sheet: str = ""
    row: int = 0
    column: int = 0
    # For neutral DocumentExtract: section/block id plus row/column for table cells.
    block_id: str = ""
    dimensions: tuple[tuple[str, str], ...] = ()
    perimeter: str = "publisher_defined"
    footnotes: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.source_locator or not self.unit or not self.unit_literal:
            raise ValueError("rosstat.binding_semantics_required")
        if bool(self.sheet) == bool(self.block_id):
            raise ValueError("rosstat.binding_one_source_coordinate_required")
        if self.row < 1 or self.column < 1:
            raise ValueError("rosstat.binding_coordinate_invalid")
        if self.geography_namespace == "oktmo" and not any(k == "geography_edition" for k, _ in self.dimensions):
            raise ValueError("rosstat.binding_geography_edition_required")


@dataclass(frozen=True, slots=True)
class ReviewedTableProfile:
    profile_id: str
    version: int
    series_id: str
    source_identity: ByteIdentity
    review_evidence: str
    bindings: tuple[CellBinding, ...]
    coverage_description: str
    territory_edition: TerritoryEdition | None = None

    def __post_init__(self):
        if not self.profile_id or self.version < 1 or not self.review_evidence or not self.bindings or not self.coverage_description:
            raise ValueError("rosstat.reviewed_profile_required")
        if len({binding.source_locator for binding in self.bindings}) != len(self.bindings):
            raise ValueError("rosstat.profile_coordinate_duplicate")
