"""Publisher-original excerpts prove bounded layouts without online test access."""
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json

import pytest

from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.data.scalars import decode_scalar
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.rosstat.tables.editions import extract_population, extract_regional_industrial_indices
from stratbox.domains.rosstat.integration.datasets import integrate_flakes
from stratbox.domains.rosstat.capabilities import contribution
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.sdk import StrategyBox

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/rosstat/reviewed_editions"


def excerpt(name):
    document = json.loads((FIXTURES / name).read_text())
    identity = ByteIdentity(**document["source_identity"])
    sheets = []
    for source_sheet in document["sheets"]:
        cells = []
        for source_cell in source_sheet["cells"]:
            values = dict(source_cell)
            values["value"] = decode_scalar(*values["value"])
            values["formula_attributes"] = tuple(tuple(item) for item in values["formula_attributes"])
            cells.append(WorkbookCell(**values))
        sheets.append(SheetCells(source_sheet["name"], source_sheet["index"], source_sheet["rows"], source_sheet["columns"],
            tuple(cells), tuple(source_sheet["merged_ranges"])))
    lineage = (UsedInputReceipt("source", identity, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only"),)
    if "container" in document:
        container = ByteIdentity(**document["container"])
        lineage = (UsedInputReceipt("regional_archive", container, "application/zip", "reference_only"),
            UsedInputReceipt("archive_member", identity, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only",
                container=container, member=document["member"]))
    workbook = WorkbookExtract(document["series_id"], document["issue_id"], document["asset_id"], identity, document["format"],
        "reviewed.publisher.excerpt", 1, tuple(sheets), lineage,
        SnapshotCoverage("partial", "Only the explicitly retained original cells in this checksummed publisher fixture."))
    return workbook, tuple(document["selected_rows"])


@pytest.mark.parametrize("year,first_value", ((2022, "468340"), (2023, "497985"), (2024, "500591")))
def test_published_population_layouts_keep_stock_date_native_geography_and_source_values(year, first_value):
    workbook, rows = excerpt(f"population-{year}.json")
    flake = extract_population(workbook, selected_rows=rows)
    assert flake.values[0].value == Decimal(first_value)
    assert {row.measure for row in flake.values} == {"total", "urban", "rural"}
    assert len(flake.values) == 3 * len(rows)
    assert flake.coverage.status == "complete"
    for row in flake.values:
        assert row.period_kind == "as_of" and row.period_start.isoformat() == str(year) + "-01-01"
        assert row.period_start == row.period_end and row.unit == "person" and row.quantity_kind == "count"
        assert dict(row.dimensions)["geography_edition"] == "rosstat.population." + str(year)
        assert row.geography_namespace == ("rosstat.terson-mo" if year == 2024 else "rosstat.population.row")
    if year == 2024:
        duplicate = [row for row in flake.values if row.geography_id == "5264141600" and row.measure == "total"]
        assert len(duplicate) == 2 and duplicate[0].key != duplicate[1].key
        assert duplicate[0].perimeter != duplicate[1].perimeter
    with StrategyBox(capabilities=CatalogSnapshot.from_contributions(contribution())) as box:
        result = box.invoke("rosstat.tables.extract_population", inputs={"workbook": workbook}, parameters={"selected_rows": rows}, timeout=20)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("flake") == flake
        plan = box.prepare_goal("source.extract", selection={"source_id": workbook.series_id, "representation": "xlsx"},
            parameters={"selected_rows": rows}, outputs=("flake",),
            supplied_outputs={"rosstat.scenario.population_extract/physical.workbook": workbook})
        assert not any(task.operation_id == "rosstat.command.tables.extract_workbook" for task in plan.tasks)
        goal = box.run(plan, timeout=20)
        assert goal.outcome == "succeeded", goal.diagnostics
        assert goal.output("flake") == flake
    dataset = integrate_flakes((flake,), dataset_id="population", release_id=str(year))
    assert all(observation.period.kind == "as_of" for observation in dataset.batch.observations)


def test_population_unreviewed_header_and_issue_date_cannot_claim_supported_layout():
    workbook, rows = excerpt("population-2024.json")
    sheet = workbook.sheets[1]
    changed = replace(sheet, cells=tuple(replace(cell, value="ОКТМО") if cell.row == 7 and cell.column == 1 else cell for cell in sheet.cells))
    with pytest.raises(ValueError, match="code_system_unreviewed"):
        extract_population(replace(workbook, sheets=(workbook.sheets[0], changed)), selected_rows=rows)
    with pytest.raises(ValueError, match="issue_date_mismatch"):
        extract_population(replace(workbook, issue_id="2023"), selected_rows=rows)


def test_regional_industrial_indices_distinguish_monthly_ytd_and_source_baseline():
    workbook, rows = excerpt("regional-industrial-2026-06.json")
    flake = extract_regional_industrial_indices(workbook, selected_rows=rows, selected_years=(2016, 2026))
    assert flake.values[0].value == Decimal("99.1")
    assert {row.frequency for row in flake.values} == {"monthly", "ytd"}
    assert {row.measure for row in flake.values} == {"year_on_year_index", "previous_period_index"}
    assert len(flake.values) == 3 * len(rows) * 24
    assert all(row.quantity_kind == "index" and row.unit == "percent" for row in flake.values)
    assert any("2023" in note for row in flake.values for note in row.footnotes)
    february_ytd = next(row for row in flake.values if row.period_end.isoformat() == "2016-02-29" and row.frequency == "ytd")
    assert february_ytd.period_start.isoformat() == "2016-01-01"
    february_month = next(row for row in flake.values if row.period_end.isoformat() == "2016-02-29" and row.frequency == "monthly")
    assert february_month.period_start.isoformat() == "2016-02-01"
    assert any(receipt.role == "archive_member" and receipt.container is not None for receipt in flake.lineage)
    dataset = integrate_flakes((flake,), dataset_id="regional.industrial", release_id="2026-06")
    with StrategyBox(capabilities=CatalogSnapshot.from_contributions(contribution())) as box:
        result = box.invoke("rosstat.tables.extract_regional_industrial_indices", inputs={"workbook": workbook},
            parameters={"selected_rows": rows, "selected_years": (2016, 2026)}, timeout=20)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("flake") == flake
        plan = box.prepare_goal("source.extract", selection={"source_id": workbook.series_id, "representation": "zip", "table_id": "industrial_production"},
            parameters={"selected_rows": rows, "selected_years": (2016, 2026)}, outputs=("flake",),
            supplied_outputs={"rosstat.scenario.regional_industrial_extract/physical.workbook": workbook})
        assert not any(task.operation_id == "rosstat.command.publications.inspect_archive" for task in plan.tasks)
        goal = box.run(plan, timeout=20)
        assert goal.outcome == "succeeded", goal.diagnostics
        assert goal.output("flake") == flake
        readable = box.invoke("rosstat.tables.readable_flake", inputs={"flake": flake}, timeout=20)
        assert readable.outcome == "succeeded", readable.diagnostics
        assert b"geography_namespace" in readable.output("representation").data
        assert b"section_notes" in readable.output("representation").data
        growth = box.invoke("rosstat.analytics.derive_index_growth", inputs={"dataset": dataset}, parameters={"release_id": "derived"}, timeout=20)
        assert growth.outcome == "succeeded", growth.diagnostics
        assert growth.output("observations").observations[0].value == Decimal("-0.9")


def test_regional_edition_and_comparison_basis_are_reviewed_not_guessed():
    workbook, rows = excerpt("regional-industrial-2026-06.json")
    with pytest.raises(ValueError, match="edition_unsupported"):
        extract_regional_industrial_indices(replace(workbook, issue_id="2025-06"), selected_rows=rows)
    sheet = workbook.sheets[1]
    changed = replace(sheet, cells=tuple(replace(cell, value="Unreviewed index basis") if cell.row == 2 and cell.column == 1 else cell for cell in sheet.cells))
    with pytest.raises(ValueError, match="basis_unreviewed"):
        extract_regional_industrial_indices(replace(workbook, sheets=(workbook.sheets[0], changed, workbook.sheets[2])), selected_rows=rows)


def test_stored_dataset_query_replays_through_generic_envelope_and_validates_family():
    from stratbox.capabilities.manifest import catalog_snapshot
    from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    from stratbox.shared.data.workbooks import workbook_snapshot
    workbook, rows = excerpt("population-2024.json")
    flake = extract_population(workbook, selected_rows=rows)
    dataset = integrate_flakes((flake,), dataset_id="population.retained", release_id="2024")
    catalog = catalog_snapshot().overlay(contribution())
    store = MemoryDatasetStore(provider_id="fixture", scope_id="rosstat")
    query = catalog.definition("query.dataset")
    read = catalog.definition("rosstat.integration.read_dataset")
    scenario = ScenarioDefinition("fixture.rosstat.query_replay", GraphBody((
        Call("query", "query.dataset", {"reference": InputRef("reference")}),
        Call("read", read.id, {"snapshot": OutputRef("query")}),
    ), {"dataset": OutputRef("read", "dataset")}), inputs=query.inputs, outputs=read.outputs)
    with StrategyBox(capabilities=catalog, providers={"dataset_writer": store, "dataset_reader": store}) as box:
        saved = box.invoke("rosstat.integration.ingest_dataset", inputs={"dataset": dataset}, timeout=15)
        assert saved.outcome == "succeeded", saved.diagnostics
        replay = box.invoke(scenario, inputs={"reference": saved.output("reference")}, timeout=15)
        assert replay.outcome == "succeeded", replay.diagnostics
        assert replay.output("dataset") == dataset
        wrong = box.invoke("ingest.observations", inputs={"value": workbook_snapshot(workbook)}, timeout=15)
        assert wrong.outcome == "succeeded", wrong.diagnostics
        rejected = box.invoke(scenario, inputs={"reference": wrong.output("value")}, timeout=15)
        assert rejected.outcome == "failed"
        assert "dataset" not in rejected.outputs
