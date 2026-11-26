"""Actual publication excerpts and explicit synthetic layouts exercise new methods."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from stratbox.domains.rosstat.domain import DOMAIN
from stratbox.domains.rosstat.methods.editions import extract_population, extract_regional_industrial_indices
from stratbox.domains.rosstat.methods.kep2 import extract_kep2, numeric_token
from stratbox.domains.rosstat.methods.types import BoundWorkbook, Kep2Settings, as_dataset
from stratbox.domains.rosstat.methods import tables, products
from stratbox.domains.rosstat.series.kep2 import RULES
from stratbox.shared.data.values import Assessment, Material, WorkbookEvidence
from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells
from stratbox.shared.data.scalars import decode_scalar
from stratbox.shared.data.coverage import SnapshotCoverage
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt
from .fixtures import synthetic_kep2_bytes


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


@pytest.fixture
def physical():
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
    material = Material(synthetic_kep2_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "rosstat.short_term_indicators", metadata={"issue_id": "2025-01"})
    evidence = WorkbookEvidence(material, read_workbook_cells(material.data))
    selected = tables.extract({"physical": evidence}, RULES, context())["tables"]
    from stratbox.domains.rosstat.methods.types import bind_workbook
    return evidence, selected, bind_workbook(selected, RULES)


def test_static_catalog_preserves_four_publications_without_inventing_pdf_tables():
    assert len(DOMAIN.common["publications"]) == 4
    assert set(DOMAIN.series) == {"rosstat.short_term_indicators", "rosstat.population_municipalities",
        "rosstat.socioeconomic_regions.industrial_production"}
    assert "national_pdf_tables" in DOMAIN.common["scientific_obligations"]
    with pytest.raises(TypeError):
        DOMAIN.series["new"] = None


def test_physical_cells_cannot_be_rebound_to_different_original_bytes(physical):
    evidence, selected, _ = physical
    unrelated = replace(evidence, material=replace(evidence.material, data=b"unrelated bytes"))
    with pytest.raises(ValueError, match="physical_material_identity_conflict"):
        tables.extract({"physical": unrelated}, RULES, context())
    from stratbox.domains.rosstat.methods.types import bind_workbook
    with pytest.raises(ValueError, match="physical_material_identity_conflict"):
        bind_workbook(replace(selected, tables=(unrelated,), material=unrelated.material), RULES)


def test_kep2_semantics_preserve_all_frequencies_raw_tokens_and_row_decisions(physical):
    evidence, selected, workbook = physical
    result = extract_kep2(Kep2Settings(workbook))
    assert result.coverage.status == "complete", result.diagnostics
    assert len({row.indicator_id for row in result.values}) == 11
    assert {row.frequency for row in result.values} == {"annual", "quarterly", "monthly"}
    source = next(row for row in result.values if row.indicator_id == "investment" and row.measure == "absolute"
        and row.frequency == "monthly" and row.period_start == date(2024, 1, 1))
    assert source.value == Decimal("110.2") and source.raw_token == "110,2 1)" and source.footnotes == ("1)",)
    assert source.period_end == date(2024, 1, 31) and source.display_date == date(2024, 2, 1)
    assert source.unit == "RUB" and source.scale == Decimal(10) ** 9
    rejected = next(row for row in result.row_decisions if not row.selected and row.indicator_id == "investment")
    assert json.loads(rejected.source_cells)["cells"][1]["raw_token"] == "1000"
    assert not any(row.indicator_id == "agriculture" and row.measure != "year_on_year_index" for row in result.values)
    freight = next(row for row in result.values if row.indicator_id == "freight_turnover"
        and row.measure == "year_on_year_index" and row.frequency == "monthly" and row.period_start.year == 2024)
    assert freight.value == Decimal("105.1") and freight.unit == "percent" and freight.quantity_kind == "index"
    dataset = tables.interpret({"tables": selected}, RULES, context())["dataset"]
    assert dataset.source_id == RULES.source_id
    assert len(dataset.semantics["row_decisions"]) == len(result.row_decisions)
    assert dataset.native is None
    use, = dataset.source_uses
    assert use.coordinate.source_id == RULES.source_id and use.coordinate.issue_id == "2025-01"
    assert use.coordinate.material_identity == evidence.material.identity
    assert use.qualification == "domain_validated"
    aligned = tables.align({"dataset": dataset}, RULES, context())["dataset"]
    assert aligned.source_uses == dataset.source_uses
    from stratbox.core.commands.standard import value_decode, value_encode
    retained = value_encode({"value": aligned}, None, context())["representation"]
    assert value_decode({"representation": retained}, None, context())["value"] == aligned
    view = products.monthly({"dataset": dataset}, None, context())["view"]
    assert {row["frequency"] for row in view.value.rows} == {"monthly"}
    encoded = products.render_monthly_workbook({"view": view}, None, context())["product"]
    from openpyxl import load_workbook
    from io import BytesIO
    book = load_workbook(BytesIO(encoded.data), data_only=True)
    assert book["Rosstat"]["C1"].value == "2024-02-01"
    assert book["Rosstat"]["C2"].value == 110.2
    assert book["Rosstat"]["D2"].value == 0
    assert book["Evidence"].max_row == len(view.value.rows) + 1


def test_kep2_duplicate_year_drift_and_ambiguous_sheet_are_rejected(physical):
    workbook = physical[2]
    with pytest.raises(ValueError, match="duplicate_year"):
        extract_kep2(Kep2Settings(workbook, duplicate_year_policy="reject"))
    sheet = next(s for s in workbook.sheets if s.name == "1.6 ")
    drift = replace(sheet, cells=tuple(replace(c, value="January-February") if c.row == 1 and c.column == 8 else c for c in sheet.cells))
    with pytest.raises(ValueError, match="period_layout_unreviewed"):
        extract_kep2(Kep2Settings(replace(workbook, sheets=tuple(drift if s.name == sheet.name else s for s in workbook.sheets))))
    with pytest.raises(ValueError, match="sheet_ambiguous"):
        extract_kep2(Kep2Settings(replace(workbook, sheets=(*workbook.sheets, replace(sheet, name="1.6", index=len(workbook.sheets))))))


def test_kep2_missing_marker_retains_partial_scope_without_stealing_next_section(physical):
    workbook = physical[2]
    sheet = next(s for s in workbook.sheets if s.name == "1.12 ")
    marker = next(c for c in sheet.cells if c.column == 1 and c.value == "в % к предыдущему периоду")
    changed = replace(sheet, cells=tuple(replace(c, value="Unknown marker") if c == marker else c for c in sheet.cells))
    result = extract_kep2(Kep2Settings(replace(workbook, sheets=tuple(changed if s.name == sheet.name else s for s in workbook.sheets))))
    assert result.coverage.status == "partial"
    assert "rosstat.kep2.marker_missing:retail:previous_period_index" in result.diagnostics
    assert not any(v.indicator_id == "retail" and v.measure == "previous_period_index" for v in result.values)


@pytest.mark.parametrize("raw,expected", [
    ("0", (Decimal(0), "reported", ())),
    ("…2)", (None, "missing", ("2)",))),
    ("—", (None, "dash", ())),
    ("20262)", (Decimal(2026), "reported", ("2)",))),
    ("157 0014)", (Decimal(157001), "reported", ("4)",))),
    ("bad token", (None, "unparsed", ())),
])
def test_numeric_tokens_remain_qualified(raw, expected):
    assert numeric_token(raw) == expected
    assert numeric_token(None, formula_without_cache=True) == (None, "unparsed", ())


def excerpt(name):
    location = Path(__file__).resolve().parents[2] / "fixtures/rosstat/reviewed_editions" / name
    document = json.loads(location.read_text())
    source = ByteIdentity(**document["source_identity"])
    sheets = []
    for sheet in document["sheets"]:
        cells = []
        for entry in sheet["cells"]:
            values = dict(entry)
            values["value"] = decode_scalar(*values["value"])
            values["formula_attributes"] = tuple(tuple(pair) for pair in values["formula_attributes"])
            cells.append(WorkbookCell(**values))
        sheets.append(SheetCells(sheet["name"], sheet["index"], sheet["rows"], sheet["columns"], tuple(cells), tuple(sheet["merged_ranges"])))
    lineage = (UsedInputReceipt("publisher_excerpt", source, "application/octet-stream", "reference_only"),)
    if "container" in document:
        container = ByteIdentity(**document["container"])
        lineage = (*lineage, UsedInputReceipt("archive_member", source, "application/octet-stream", "reference_only", container=container, member=document["member"]))
    return BoundWorkbook(document["series_id"], document["issue_id"], document["asset_id"], source,
        ByteIdentity.of(location.read_bytes()), tuple(sheets), lineage,
        SnapshotCoverage("partial", "Exact retained publisher original cells.")), tuple(document["selected_rows"])


@pytest.mark.parametrize("year,first", ((2022, "468340"), (2023, "497985"), (2024, "500591")))
def test_publisher_population_excerpts_keep_native_territories_and_stock_dates(year, first):
    workbook, rows = excerpt(f"population-{year}.json")
    table = extract_population(workbook, selected_rows=rows)
    assert table.values[0].value == Decimal(first)
    assert len(table.values) == 3 * len(rows)
    assert {row.measure for row in table.values} == {"total", "urban", "rural"}
    assert table.coverage.status == "complete"
    for row in table.values:
        assert row.period_kind == "as_of" and row.period_start == row.period_end == date(year, 1, 1)
        assert row.geography_namespace == ("rosstat.terson-mo" if year == 2024 else "rosstat.population.row")
        assert row.unit == "person" and row.quantity_kind == "count"
    if year == 2024:
        duplicate = [row for row in table.values if row.geography_id == "5264141600" and row.measure == "total"]
        assert len(duplicate) == 2 and duplicate[0].key != duplicate[1].key
        assert duplicate[0].perimeter != duplicate[1].perimeter
    dataset = as_dataset(table)
    assert all(row["period_kind"] == "as_of" for row in dataset.rows)


def test_population_rejects_invented_oktmo_header_or_wrong_issue():
    workbook, rows = excerpt("population-2024.json")
    sheet = workbook.sheets[1]
    changed = replace(sheet, cells=tuple(replace(cell, value="OKTMO") if cell.row == 7 and cell.column == 1 else cell for cell in sheet.cells))
    with pytest.raises(ValueError, match="code_system_unreviewed"):
        extract_population(replace(workbook, sheets=(workbook.sheets[0], changed)), selected_rows=rows)
    with pytest.raises(ValueError, match="issue_date_mismatch"):
        extract_population(replace(workbook, issue_id="2023"), selected_rows=rows)


def test_publisher_regional_industrial_excerpts_keep_ytd_and_monthly_bases():
    workbook, rows = excerpt("regional-industrial-2026-06.json")
    table = extract_regional_industrial_indices(workbook, selected_rows=rows, selected_years=(2016, 2026))
    assert table.values[0].value == Decimal("99.1")
    assert {row.frequency for row in table.values} == {"monthly", "ytd"}
    assert len(table.values) == 3 * len(rows) * 24
    assert any(row.period_start == date(2016, 1, 1) and row.period_end == date(2016, 2, 29) for row in table.values if row.frequency == "ytd")
    assert any(row.period_start == date(2016, 2, 1) and row.period_end == date(2016, 2, 29) for row in table.values if row.frequency == "monthly")
    assert any(receipt.role == "archive_member" and receipt.container is not None for receipt in table.lineage)
    with pytest.raises(ValueError, match="edition_unsupported"):
        extract_regional_industrial_indices(replace(workbook, issue_id="2025-06"), selected_rows=rows)
    second = workbook.sheets[1]
    changed = replace(second, cells=tuple(replace(cell, value="Unknown basis") if cell.row == 2 and cell.column == 1 else cell for cell in second.cells))
    with pytest.raises(ValueError, match="basis_unreviewed"):
        extract_regional_industrial_indices(replace(workbook, sheets=(workbook.sheets[0], changed, workbook.sheets[2])), selected_rows=rows)
