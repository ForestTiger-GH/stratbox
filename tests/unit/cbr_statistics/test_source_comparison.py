"""Source revisions distinguish published facts, formulas and workbook layout."""
from dataclasses import replace
from decimal import Decimal

import pytest

from stratbox.core.formats.spreadsheets.cells import SheetCells, WorkbookCell
from stratbox.domains.cbr.publications.catalog import source
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
from stratbox.domains.cbr.tables.statistics.validation import compare_workbook_flakes, validate_workbook_flake
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


def _flake(*, token="123", formula=None, original=b"before", issue="capture-1", sheets=None):
    series = source("cbr.monetary_statistics.monetary_agg")
    identity = ByteIdentity.of(original)
    cell = WorkbookCell(1, 1, "A1", Decimal(token), token, "n", formula)
    return WorkbookFlake(series.series_id, issue, identity, series.table_profile, 1,
        sheets if sheets is not None else (SheetCells("Денежные агрегаты", 0, 2, 2, (cell,)),),
        (UsedInputReceipt("original", identity, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          "inline", series.series_id),))


def test_numeric_revision_keeps_exact_cells_and_two_source_versions():
    before, after = _flake(), _flake(token="124.00", original=b"after")
    result = compare_workbook_flakes(before, after)
    assert result.source_change == "facts_changed"
    assert len(result.fact_changes) == 1
    change = result.fact_changes[0]
    assert change.before.value == Decimal("123")
    assert change.after.value == Decimal("124.00")
    assert change.after.raw_token == "124.00"
    assert result.before_flake == before.identity
    assert result.after_flake == after.identity
    assert result.identity == compare_workbook_flakes(before, after).identity


def test_numeric_lexical_precision_is_not_a_changed_published_value():
    result = compare_workbook_flakes(_flake(), _flake(token="123.00", original=b"after"))
    assert result.source_change == "source_structure_changed"
    assert result.fact_changes == ()
    assert result.changes[0].before.raw_token == "123"
    assert result.changes[0].after.raw_token == "123.00"
    assert "raw_token" in result.changes[0].changed_fields


def test_equal_cached_values_do_not_hide_changed_formulas_or_their_attributes():
    before = _flake(formula="SUM(B1:B2)")
    after = _flake(formula="B1+B2", original=b"after")
    sheet = after.sheets[0]
    cell = replace(sheet.cells[0], formula_attributes=(("t", "array"), ("ref", "A1")))
    after = replace(after, sheets=(replace(sheet, cells=(cell,)),))
    result = compare_workbook_flakes(before, after)
    assert result.source_change == "source_structure_changed"
    assert result.fact_changes == ()
    assert result.formula_changes == result.changes
    assert result.formula_changes[0].before.formula == "SUM(B1:B2)"
    assert result.formula_changes[0].after.formula == "B1+B2"
    assert result.formula_changes[0].after.formula_attributes == (("t", "array"), ("ref", "A1"))
    # A formula is part of result evidence even when its cached scalar agrees.
    rewritten = replace(result.changes[0], after=replace(cell, formula="B2+B1"))
    assert replace(result, changes=(rewritten,)).identity != result.identity


def test_sheet_order_extents_merges_and_empty_sheets_are_structural_revisions():
    before = _flake()
    sheet = before.sheets[0]
    after = _flake(original=b"after", sheets=(
        SheetCells("Notes", 0, 0, 0, ()),
        replace(sheet, index=1, rows=3, columns=4, merged_ranges=("A2:B2",)),
    ))
    result = compare_workbook_flakes(before, after)
    assert result.source_change == "source_structure_changed"
    assert result.changes == result.fact_changes == ()
    changes = {item.sheet: item for item in result.layout_changes}
    assert changes["Notes"].before is None
    assert changes["Notes"].after.rows == 0
    assert changes[sheet.name].changed_fields == ("index", "rows", "columns", "merged_ranges")
    assert changes[sheet.name].after.merged_ranges == ("A2:B2",)
    reverse = compare_workbook_flakes(after, before)
    assert next(item for item in reverse.layout_changes if item.sheet == "Notes").after is None


def test_explicit_blank_cells_are_source_structure_and_boolean_is_a_separate_fact():
    before = _flake(token="1")
    sheet = before.sheets[0]
    blank = WorkbookCell(2, 1, "A2", None, None, "n")
    after = _flake(original=b"blank", sheets=(replace(sheet, cells=(*sheet.cells, blank)),))
    comparison = compare_workbook_flakes(before, after)
    assert comparison.source_change == "source_structure_changed"
    assert comparison.fact_changes == ()
    boolean = replace(sheet.cells[0], value=True, raw_token="1", kind="b")
    after = _flake(original=b"boolean", sheets=(replace(sheet, cells=(boolean,)),))
    assert compare_workbook_flakes(before, after).source_change == "facts_changed"


def test_same_bytes_with_conflicting_cells_or_layout_fail_closed():
    before = _flake()
    with pytest.raises(ValueError, match="comparison_source_evidence_conflict"):
        compare_workbook_flakes(before, _flake(token="124"))
    changed_layout = replace(before, sheets=(replace(before.sheets[0], merged_ranges=("A2:B2",)),))
    with pytest.raises(ValueError, match="comparison_source_evidence_conflict"):
        compare_workbook_flakes(before, changed_layout)


def test_same_source_under_changed_caller_issue_is_distinct_from_byte_revision():
    before = _flake()
    repeated = compare_workbook_flakes(before, _flake(issue="capture-2"))
    assert repeated.source_change == "unchanged"
    assert repeated.issue_change == "different_caller_issue"
    repacked = compare_workbook_flakes(before, _flake(original=b"repacked"))
    assert repacked.source_change == "bytes_revised"
    assert repacked.changes == repacked.layout_changes == ()


@pytest.mark.parametrize("update", [{"profile_id": "different-profile"}, {"profile_version": 2}])
def test_changed_interpretation_profile_is_not_treated_as_a_source_revision(update):
    before = _flake()
    with pytest.raises(ValueError, match="comparison_profile_mismatch"):
        compare_workbook_flakes(before, replace(_flake(original=b"after"), **update))


def test_duplicate_coordinates_cannot_disappear_during_comparison():
    before = _flake()
    sheet = before.sheets[0]
    malformed = _flake(original=b"after", sheets=(replace(sheet, cells=sheet.cells * 2),))
    with pytest.raises(ValueError, match="coordinate_invalid"):
        compare_workbook_flakes(before, malformed)


def test_validation_has_stable_qualified_output_identity():
    flake = _flake(formula="B1+B2")
    report = validate_workbook_flake(flake)
    assert report.flake_identity == flake.identity
    assert report.profile_id == flake.profile_id
    assert report.identity == validate_workbook_flake(flake).identity
