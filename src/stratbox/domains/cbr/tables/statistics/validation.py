"""Source validation and revision comparison without downstream recomputation."""
from decimal import Decimal

from .contracts import (CellChange, SheetChange, SheetLayout, TableDiagnostic,
                        WorkbookComparison, WorkbookFlake, WorkbookValidation)
from .profiles import table_profile, sheet_variant
from .scalars import encode_scalar
from .snapshots import flake_snapshot


def validate_workbook_flake(flake):
    snapshot = flake_snapshot(flake)
    profile = table_profile(flake.profile_id)
    if profile.series_id != flake.series_id or profile.version != flake.profile_version:
        raise ValueError("cbr.workbook.profile_mismatch")
    diagnostics, tables = [], []
    for sheet in flake.sheets:
        variant = sheet_variant(profile, sheet.name)
        if variant is None:
            diagnostics.append(TableDiagnostic("cbr.workbook.layout_unrecognized", sheet.name))
        else:
            tables.append((sheet.name, variant.variant_id))
        for cell in sheet.cells:
            if cell.formula is not None and cell.value is None:
                diagnostics.append(TableDiagnostic("cbr.workbook.formula_cache_missing", sheet.name, cell.coordinate))
            if cell.kind == "e":
                diagnostics.append(TableDiagnostic("cbr.workbook.source_cell_error", sheet.name, cell.coordinate, str(cell.value)))
    return WorkbookValidation(flake.series_id, flake.source_identity, tuple(diagnostics), tuple(tables),
                              flake.profile_id, flake.profile_version, snapshot.identity)


def _same_value(left, right):
    # Numeric precision and OOXML scalar encoding are separate from the value.
    # Boolean True and numeric 1 must remain different published facts.
    if type(left) in {int, Decimal} and type(right) in {int, Decimal}:
        return left == right
    return encode_scalar(left) == encode_scalar(right)


def _cell_fields(left, right):
    if left is None or right is None:
        present = left if left is not None else right
        return ("presence", *(("value",) if present.value is not None else ()),
                *(("formula",) if present.formula is not None else ()),
                *(("formula_attributes",) if present.formula_attributes else ()))
    result = []
    if not _same_value(left.value, right.value):
        result.append("value")
    elif encode_scalar(left.value) != encode_scalar(right.value):
        result.append("value_encoding")
    for field in ("raw_token", "kind", "formula", "formula_attributes", "number_format", "indent"):
        if getattr(left, field) != getattr(right, field):
            result.append(field)
    return tuple(result)


def _layout_changes(before, after):
    old = {sheet.name: SheetLayout(sheet.index, sheet.rows, sheet.columns, sheet.merged_ranges)
           for sheet in before.sheets}
    new = {sheet.name: SheetLayout(sheet.index, sheet.rows, sheet.columns, sheet.merged_ranges)
           for sheet in after.sheets}
    result = []
    for name in sorted(old.keys() | new.keys()):
        left, right = old.get(name), new.get(name)
        if left == right:
            continue
        fields = (("presence",) if left is None or right is None else tuple(
            field for field in ("index", "rows", "columns", "merged_ranges")
            if getattr(left, field) != getattr(right, field)))
        result.append(SheetChange(name, left, right, fields))
    return tuple(result)


def compare_workbook_flakes(before, after):
    if not isinstance(before, WorkbookFlake) or not isinstance(after, WorkbookFlake):
        raise ValueError("cbr.workbook.flake_required")
    if before.series_id != after.series_id:
        raise ValueError("cbr.workbook.comparison_series_mismatch")
    if before.asset_id != after.asset_id:
        raise ValueError("cbr.workbook.comparison_asset_mismatch")
    if (before.profile_id, before.profile_version) != (after.profile_id, after.profile_version):
        raise ValueError("cbr.workbook.comparison_profile_mismatch")
    # Admission precedes maps so duplicate coordinates cannot disappear in a
    # dict, and changed parser profiles cannot masquerade as source revisions.
    before_snapshot, after_snapshot = flake_snapshot(before), flake_snapshot(after)
    # These maps contain source-local evidence, never output formatting.
    old = {(sheet.name, cell.coordinate): cell for sheet in before.sheets for cell in sheet.cells}
    new = {(sheet.name, cell.coordinate): cell for sheet in after.sheets for cell in sheet.cells}
    changes = []
    for sheet, coordinate in sorted(old.keys() | new.keys()):
        left, right = old.get((sheet, coordinate)), new.get((sheet, coordinate))
        fields = _cell_fields(left, right)
        if not fields:
            continue
        kind = "added" if left is None else "removed" if right is None else (
            "value_changed" if "value" in fields else "formula_changed"
            if {"formula", "formula_attributes"}.intersection(fields) else "source_structure_changed")
        changes.append(CellChange(sheet, coordinate, left, right, kind, fields))
    layouts = _layout_changes(before, after)
    if before.source_identity == after.source_identity and (changes or layouts):
        raise ValueError("cbr.workbook.comparison_source_evidence_conflict")
    state = ("unchanged" if before.source_identity == after.source_identity else
             "facts_changed" if any("value" in item.changed_fields for item in changes) else
             "source_structure_changed" if changes or layouts else "bytes_revised")
    issue = "same_issue" if before.issue_id == after.issue_id else "different_caller_issue"
    return WorkbookComparison(before.series_id, state, issue, tuple(changes), before.source_identity, after.source_identity,
                              before_snapshot.identity, after_snapshot.identity, before.profile_id, before.profile_version,
                              layouts)
