"""Compare retained physical facts, formulas, lexical evidence and worksheet layout."""
from dataclasses import dataclass
from decimal import Decimal
import re

from stratbox.shared.data.values import TableEvidenceSet, WorkbookEvidence, fingerprint
from stratbox.shared.data.workbook_cells import WorkbookCell, validate_sheet_cells
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True)
class CellChange:
    sheet: str
    coordinate: str
    before: WorkbookCell | None
    after: WorkbookCell | None
    kind: str
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class SheetLayout:
    index: int
    rows: int
    columns: int
    merged_ranges: tuple[str, ...]


@dataclass(frozen=True)
class SheetChange:
    sheet: str
    before: SheetLayout | None
    after: SheetLayout | None
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class WorkbookComparison:
    source_id: str | None
    source_change: str
    issue_change: str
    changes: tuple[CellChange, ...]
    before: ByteIdentity
    after: ByteIdentity
    before_evidence: str
    after_evidence: str
    layout_changes: tuple[SheetChange, ...] = ()

    @property
    def fact_changes(self):
        return tuple(item for item in self.changes if "value" in item.changed_fields)

    @property
    def formula_changes(self):
        return tuple(item for item in self.changes if {"formula", "formula_attributes"}.intersection(item.changed_fields))

    @property
    def identity(self):
        return fingerprint(self)


def _admit(value, checkpoint=None):
    if isinstance(value, WorkbookEvidence):
        material, sheets = value.material, value.workbook.sheets
        if material.identity != value.workbook.identity:
            raise ValueError("cbr.workbook.material_identity_mismatch")
        source = material.source_id
        issue = material.metadata.get("issue_id", "")
        asset = material.metadata.get("asset_id", "main")
    elif isinstance(value, TableEvidenceSet) and value.material is not None:
        material, sheets = value.material, value.tables
        source, issue, asset = value.source_id, value.issue_id, value.metadata.get("asset_id", "main")
        if material.source_id not in {None, source}:
            raise ValueError("cbr.workbook.source_mismatch")
    else:
        raise ValueError("cbr.workbook.physical_evidence_required")
    if not isinstance(asset, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", asset):
        raise ValueError("source.identity_token_invalid")
    if len({sheet.name for sheet in sheets}) != len(sheets) or len({sheet.index for sheet in sheets}) != len(sheets):
        raise ValueError("cbr.workbook.sheet_identity_duplicate")
    for sheet in sheets:
        validate_sheet_cells(sheet, checkpoint=checkpoint)
    return source, issue, asset, material.identity, tuple(sheets)


def validate_workbook(value, *, checkpoint=None):
    """Validate retained evidence without opening the original or interpreting economics."""
    _, _, _, _, sheets = _admit(value, checkpoint)
    findings = []
    for sheet in sheets:
        for cell in sheet.cells:
            if cell.formula is not None and cell.value is None:
                findings.append(("cbr.workbook.formula_cache_missing", sheet.name, cell.coordinate))
            if cell.kind == "e":
                findings.append(("cbr.workbook.source_cell_error", sheet.name, cell.coordinate))
    return tuple(findings)


def _same_value(left, right):
    if type(left) in {int, Decimal} and type(right) in {int, Decimal}:
        return left == right
    return fingerprint(left) == fingerprint(right)


def _cell_fields(left, right):
    if left is None or right is None:
        present = left if left is not None else right
        return ("presence", *(("value",) if present.value is not None else ()),
                *(("formula",) if present.formula is not None else ()),
                *(("formula_attributes",) if present.formula_attributes else ()))
    changed = []
    if not _same_value(left.value, right.value):
        changed.append("value")
    elif fingerprint(left.value) != fingerprint(right.value):
        changed.append("value_encoding")
    for name in ("raw_token", "kind", "formula", "formula_attributes", "number_format", "indent", "evidence_kind"):
        if getattr(left, name) != getattr(right, name):
            changed.append(name)
    return tuple(changed)


def compare_workbooks(before, after, *, checkpoint=None):
    old_source, old_issue, old_asset, old_identity, old_sheets = _admit(before, checkpoint)
    new_source, new_issue, new_asset, new_identity, new_sheets = _admit(after, checkpoint)
    if old_source != new_source:
        raise ValueError("cbr.workbook.comparison_series_mismatch")
    if old_asset != new_asset:
        raise ValueError("cbr.workbook.comparison_asset_mismatch")
    old = {(sheet.name, cell.coordinate): cell for sheet in old_sheets for cell in sheet.cells}
    new = {(sheet.name, cell.coordinate): cell for sheet in new_sheets for cell in sheet.cells}
    changes = []
    for sheet, coordinate in sorted(old.keys() | new.keys()):
        if checkpoint is not None:
            checkpoint()
        left, right = old.get((sheet, coordinate)), new.get((sheet, coordinate))
        fields = _cell_fields(left, right)
        if fields:
            kind = "added" if left is None else "removed" if right is None else (
                "value_changed" if "value" in fields else "formula_changed"
                if {"formula", "formula_attributes"}.intersection(fields) else "source_structure_changed")
            changes.append(CellChange(sheet, coordinate, left, right, kind, fields))
    old_layout = {sheet.name: SheetLayout(sheet.index, sheet.rows, sheet.columns, sheet.merged_ranges) for sheet in old_sheets}
    new_layout = {sheet.name: SheetLayout(sheet.index, sheet.rows, sheet.columns, sheet.merged_ranges) for sheet in new_sheets}
    layouts = []
    for name in sorted(old_layout.keys() | new_layout.keys()):
        left, right = old_layout.get(name), new_layout.get(name)
        if left != right:
            fields = ("presence",) if left is None or right is None else tuple(field for field in (
                "index", "rows", "columns", "merged_ranges") if getattr(left, field) != getattr(right, field))
            layouts.append(SheetChange(name, left, right, fields))
    if old_identity == new_identity and (changes or layouts):
        raise ValueError("cbr.workbook.comparison_source_evidence_conflict")
    state = ("unchanged" if old_identity == new_identity else "facts_changed" if any(
        "value" in item.changed_fields for item in changes) else "source_structure_changed" if changes or layouts else "bytes_revised")
    return WorkbookComparison(old_source, state, "same_issue" if old_issue == new_issue else "different_caller_issue",
        tuple(changes), old_identity, new_identity, fingerprint(before), fingerprint(after), tuple(layouts))
