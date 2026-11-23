"""Exact source cells, retained semantics and independent product rendering."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile
import json

import pytest
from openpyxl import Workbook, load_workbook

from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.shared.data.observations import PeriodRef
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot, flake_from_snapshot
from stratbox.domains.cbr.tables.statistics.validation import validate_workbook_flake, compare_workbook_flakes
from stratbox.domains.cbr.tables.statistics.readable import readable_workbook
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot, dataset_from_snapshot
from stratbox.domains.cbr.analytics.statistics.changes import calculate_change
from stratbox.domains.cbr.products.statistics.views import build_view, view_from_snapshot
from stratbox.domains.cbr.products.statistics.rendering import render_view


def workbook(*, exact="9007199254740993.00", name="Денежные агрегаты"):
    book = Workbook()
    sheet = book.active
    sheet.title = name
    sheet.append(["Monetary aggregate, млрд руб.", date(2026, 1, 1), date(2026, 2, 1)])
    sheet.append(["M2", 123, 456])
    sheet.append(["Unavailable", "—", None])
    sheet.append(["Formula", "=SUM(B2:C2)", 0])
    sheet.merge_cells("A6:C6")
    sheet["A6"] = "Methodology stays attached"
    out = BytesIO(); book.save(out)
    return rewrite(out.getvalue(), lambda name, data: data.replace(b"<v>123</v>", ("<v>" + exact + "</v>").encode())
                   if name == "xl/worksheets/sheet1.xml" else data)


def rewrite(data, fn):
    out = BytesIO()
    with ZipFile(BytesIO(data)) as old, ZipFile(out, "w") as new:
        for name in old.namelist():
            new.writestr(name, fn(name, old.read(name)))
    return out.getvalue()


def flake(data=None):
    series = "cbr.monetary_statistics.monetary_agg"
    payload = SourcePayload(data or workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", series)
    return extract_workbook_value(IdentifiedOriginal(SourceAssetIdentity(series, "capture-1", "main"), payload, "xlsx"))


def test_exact_numeric_lexeme_formulas_blank_and_merges_survive_source_replay():
    value = flake()
    cell = value.sheets[0].cell(2, 2)
    assert cell.value == Decimal("9007199254740993.00")
    assert cell.raw_token == "9007199254740993.00"
    assert value.sheets[0].cell(4, 2).formula == "SUM(B2:C2)"
    assert value.sheets[0].cell(4, 2).value is None
    assert value.sheets[0].merged_ranges == ("A6:C6",)
    restored = flake_from_snapshot(flake_snapshot(value))
    assert restored == value
    validation = validate_workbook_flake(restored)
    assert {item.code for item in validation.diagnostics} == {"cbr.workbook.formula_cache_missing"}
    rows = [json.loads(line) for line in readable_workbook(restored).data.splitlines()]
    assert any(row.get("raw_token") == "9007199254740993.00" for row in rows)


def test_retained_dataset_and_view_render_without_original_or_parser(monkeypatch):
    original = flake()
    data = align_statistics((flake_from_snapshot(flake_snapshot(original)),))
    rebuilt = dataset_from_snapshot(dataset_snapshot(data))
    assert rebuilt == data
    target = next(item.metric.id for item in rebuilt.batches[0].observations if dict(item.dimensions)["source_hierarchy"] == "M2")
    view = build_view(rebuilt, metric_ids=(target,))
    def forbidden(*args, **kwargs):
        raise AssertionError("A renderer must consume only the prepared view")
    monkeypatch.setattr("stratbox.domains.cbr.tables.statistics.extraction.read_workbook_cells", forbidden)
    restored = view_from_snapshot(view.snapshot)
    representation = render_view(restored)
    assert render_view(restored).identity == representation.identity
    book = load_workbook(BytesIO(representation.data), data_only=False)
    try:
        assert book["Observations"]["H2"].value == "9007199254740993.00"
        assert book["Inputs"].max_row == 2
    finally:
        book.close()


def test_computed_growth_has_distinct_measure_basis_and_exact_input_vector():
    dataset = align_statistics((flake(workbook(exact="123")),))
    # Restrict to a qualified metric, retaining the full original version vector.
    batch = dataset.batches[0]
    items = tuple(item for item in batch.observations if dict(item.dimensions)["source_hierarchy"] == "M2")
    selected = replace(dataset, batches=(replace(batch, observations=items),))
    result = calculate_change(selected, PeriodRef("as_of", as_of=date(2026, 1, 1)),
                              PeriodRef("as_of", as_of=date(2026, 2, 1)), method="growth_percent")
    assert result.inputs == dataset.inputs
    observation = result.batches[0].observations[0]
    assert observation.value == (Decimal(456) / 123 - 1) * 100
    assert dict(observation.dimensions)["measure_basis"] == "computed_growth_percent"
    assert observation.metric.id != items[0].metric.id
    assert any(item.role == "integrated_statistics" for item in result.lineage)


def test_byte_revision_and_source_fact_change_are_separate():
    before = flake(workbook(exact="123"))
    after = flake(workbook(exact="124"))
    difference = compare_workbook_flakes(before, after)
    assert difference.source_change == "facts_changed"
    assert difference.issue_change == "same_issue"
    assert [item.coordinate for item in difference.changes] == ["B2"]


@pytest.mark.parametrize("mutation, diagnostic", [
    (lambda name, data: data.replace(b"http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                                    b"http://purl.oclc.org/ooxml/spreadsheetml/main"), "namespace_unsupported"),
    (lambda name, data: data.replace(b'<c r="B2"', b'<c s="-1" r="B2"') if name.endswith("sheet1.xml") else data, "invalid_cell"),
])
def test_unreviewed_namespace_and_negative_style_index_fail_closed(mutation, diagnostic):
    with pytest.raises(ValueError, match=diagnostic):
        read_workbook_cells(rewrite(workbook(), mutation))


def test_forged_profile_or_numeric_lexeme_cannot_be_retained_as_a_complete_flake():
    value = flake()
    with pytest.raises(ValueError, match="binding_invalid"):
        flake_snapshot(replace(value, profile_id="bogus"))
    sheet = value.sheets[0]
    cells = tuple(replace(cell, value=999) if cell.coordinate == "B2" else cell for cell in sheet.cells)
    with pytest.raises(ValueError, match="numeric_evidence_mismatch"):
        flake_snapshot(replace(value, sheets=(replace(sheet, cells=cells),)))
