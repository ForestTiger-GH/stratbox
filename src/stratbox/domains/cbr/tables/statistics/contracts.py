"""Complete source workbooks, before economic interpretation or selection."""
from dataclasses import dataclass
import re

from stratbox.core.formats.spreadsheets.cells import SheetCells, WorkbookCell
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.data.scalars import encode_scalar


@dataclass(frozen=True, slots=True)
class WorkbookFlake:
    series_id: str
    issue_id: str
    source_identity: ByteIdentity
    profile_id: str
    profile_version: int
    sheets: tuple[SheetCells, ...]
    lineage: tuple[UsedInputReceipt, ...] = ()
    coverage: SnapshotCoverage = SnapshotCoverage("complete", "Every worksheet in the supplied original; historical publication inventory is unspecified.")
    asset_id: str = "main"

    @property
    def identity(self):
        from .snapshots import flake_snapshot
        return flake_snapshot(self).identity


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

    def __post_init__(self):
        if self.unit_anchor is not None and (not isinstance(self.unit_anchor, str)
                or re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", self.unit_anchor) is None):
            raise ValueError("cbr.statistics.unit_anchor_invalid")


@dataclass(frozen=True, slots=True)
class SourceTableProfile:
    profile_id: str
    series_id: str
    version: int
    edition: str
    variants: tuple[TableVariant, ...]
    extraction_scope: str
    integration_scope: str


@dataclass(frozen=True, slots=True)
class TableDiagnostic:
    code: str
    sheet: str
    coordinate: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class WorkbookValidation:
    series_id: str
    source_identity: ByteIdentity
    diagnostics: tuple[TableDiagnostic, ...]
    recognized_tables: tuple[tuple[str, str], ...]
    profile_id: str
    profile_version: int
    flake_identity: ByteIdentity

    @property
    def identity(self):
        return ByteIdentity.of(canonical_manifest_bytes({
            "contract": "cbr.workbook.validation.v1", "series_id": self.series_id,
            "source": _byte_evidence(self.source_identity), "flake": _byte_evidence(self.flake_identity),
            "profile": [self.profile_id, self.profile_version], "tables": self.recognized_tables,
            "diagnostics": [[item.code, item.sheet, item.coordinate, item.detail] for item in self.diagnostics],
        }))


@dataclass(frozen=True, slots=True)
class CellChange:
    """Full source cells keep formulas, cache values and precision inspectable."""
    sheet: str
    coordinate: str
    before: WorkbookCell | None
    after: WorkbookCell | None
    kind: str
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SheetLayout:
    index: int
    rows: int
    columns: int
    merged_ranges: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SheetChange:
    sheet: str
    before: SheetLayout | None
    after: SheetLayout | None
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkbookComparison:
    series_id: str
    source_change: str
    issue_change: str
    changes: tuple[CellChange, ...]
    before: ByteIdentity
    after: ByteIdentity
    before_flake: ByteIdentity
    after_flake: ByteIdentity
    profile_id: str
    profile_version: int
    layout_changes: tuple[SheetChange, ...] = ()

    @property
    def fact_changes(self):
        """Published scalar changes, independent of formula or lexical changes."""
        return tuple(item for item in self.changes if "value" in item.changed_fields)

    @property
    def formula_changes(self):
        return tuple(item for item in self.changes
                     if {"formula", "formula_attributes"}.intersection(item.changed_fields))

    @property
    def identity(self):
        return ByteIdentity.of(canonical_manifest_bytes({
            "contract": "cbr.workbook.comparison.v1", "series_id": self.series_id,
            "source_change": self.source_change, "issue_change": self.issue_change,
            "before": _byte_evidence(self.before), "after": _byte_evidence(self.after),
            "before_flake": _byte_evidence(self.before_flake), "after_flake": _byte_evidence(self.after_flake),
            "profile": [self.profile_id, self.profile_version],
            "changes": [[item.sheet, item.coordinate, _cell_evidence(item.before), _cell_evidence(item.after),
                         item.kind, item.changed_fields] for item in self.changes],
            "layout_changes": [[item.sheet, _layout_evidence(item.before), _layout_evidence(item.after),
                                 item.changed_fields] for item in self.layout_changes],
        }))


def _byte_evidence(value):
    return [value.sha256, value.size]


def _cell_evidence(value):
    if value is None:
        return None
    return [value.row, value.column, value.coordinate, encode_scalar(value.value), value.raw_token,
            value.kind, value.formula, value.number_format, value.indent, value.formula_attributes]


def _layout_evidence(value):
    return None if value is None else [value.index, value.rows, value.columns, value.merged_ranges]
