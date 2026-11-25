"""Canonical Rosstat commands preserve evidence and independent replay boundaries."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.domains.rosstat.capabilities import contribution, dispositions, stage_matrix
from stratbox.sdk import StrategyBox
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.data.documents import DocumentExtract, DocumentBlock
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.data.workbooks import workbook_snapshot
from stratbox.domains.rosstat.tables.contracts import ReviewedTableProfile, CellBinding
from stratbox.domains.rosstat.tables.documents import ReviewedDocumentLayout, DocumentTableRegion
from stratbox.core.formats.spreadsheets.extracts import extract_workbook

from test_kep2_route import native_workbook, physical
from test_family_routes import _binding, _edition, _workbook_bytes


def snapshot():
    return CatalogSnapshot.from_contributions(contribution())


def errors(result):
    return [diagnostic.code for value in result.results.values() for diagnostic in value.diagnostics]


def test_domain_catalog_is_lazy_complete_and_has_exact_source_recipes():
    script = '''
import sys
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.domains.rosstat.capabilities import contribution
catalog=CatalogSnapshot.from_contributions(contribution())
assert len(catalog.groups)==4
assert len(catalog.profiles)==10
assert not {'pandas','numpy','openpyxl','pypdf'} & sys.modules.keys()
'''
    subprocess.run([sys.executable, "-c", script], check=True, env={**os.environ, "PYTHONPATH": "src"})
    catalog = snapshot()
    root = Path(__file__).resolve().parents[3]
    identifiers = {json.loads(path.read_text())["definition"]["operation_id"]
        for path in (root / "src/stratbox/operations/specifications/domains/rosstat/operations").rglob("OPERATION_*.yaml")}
    assert identifiers == {item["operation_id"] for item in dispositions()}
    assert len(identifiers) == 36
    for item in dispositions():
        assert catalog.definition(item["capability_id"]).kind == item["kind"]
    for source_id, representation in (("rosstat.short_term_indicators", "xlsx"),
            ("rosstat.socioeconomic_russia", "pdf"), ("rosstat.socioeconomic_regions", "zip"),
            ("rosstat.population_municipalities", "xlsx")):
        recipe = catalog.resolve_goal("source.extract", selection={"source_id": source_id, "representation": representation})
        assert recipe.defaults["series_id"] == source_id
    assert {row["source_id"] for row in stage_matrix()} == {group.source_ids[0] for group in catalog.groups}


def test_kep2_canonical_product_replays_all_frequencies_then_monthly_product(native_workbook, monkeypatch):
    from stratbox.domains.rosstat.operations import handlers
    monkeypatch.setattr(handlers, "extract_kep2", lambda *a, **k: pytest.fail("nested operation handler"))
    with StrategyBox(capabilities=snapshot()) as box:
        result = box.invoke("rosstat.scenario.kep2_product",
            inputs={"payload": SourcePayload(native_workbook)}, parameters={"series_id": "rosstat.short_term_indicators",
                "issue_id": "2025-01", "asset_id": "main_workbook", "dataset_id": "kep2.fixture", "release_id": "v1"}, timeout=30)
        assert result.outcome == "succeeded", errors(result)
        flake, dataset = result.output("flake"), result.output("dataset")
        assert len({row.indicator_id for row in flake.values}) == 11
        assert {row.frequency for row in flake.values} == {"annual", "quarterly", "monthly"}
        source_identity = flake.source_identity
        assert any(receipt.identity == source_identity for receipt in dataset.batch.lineage)
        saved = box.invoke("rosstat.integration.dataset_snapshot", inputs={"dataset": dataset}, timeout=30)
        assert saved.outcome == "succeeded", errors(saved)
        monkeypatch.setattr("stratbox.core.formats.spreadsheets.extracts.extract_workbook", lambda *a, **k: pytest.fail("decode during replay"))
        replay = box.invoke("rosstat.integration.read_dataset", inputs={"snapshot": saved.output("snapshot")}, timeout=30)
        assert replay.outcome == "succeeded", errors(replay)
        assert replay.output("dataset") == dataset
        monthly = box.invoke("rosstat.scenario.kep2_monthly", inputs={"dataset": replay.output("dataset")}, timeout=30)
        assert monthly.outcome == "succeeded", errors(monthly)
        assert {dict(row.dimensions)["frequency"] for row in monthly.output("view").batch.observations} == {"monthly"}
        assert monthly.output("representation").data.startswith(b"PK")
        growth = box.invoke("rosstat.analytics.derive_index_growth", inputs={"dataset": dataset}, parameters={"release_id": "growth"}, timeout=30)
        assert growth.outcome == "succeeded", errors(growth)
        assert any(row.value == Decimal("5.1") and row.value_status == "derived" for row in growth.output("observations").observations)
        assert all(row.value_status != "derived" for row in dataset.batch.observations)


def test_supplied_kep2_flake_prunes_physical_read_and_retains_operation_scope(physical):
    with StrategyBox(capabilities=snapshot()) as box:
        flake = box.invoke("rosstat.tables.extract_kep2", inputs={"workbook": physical}, timeout=30)
        assert flake.outcome == "succeeded", errors(flake)
        plan = box.prepare("rosstat.scenario.kep2_product", supplied_outputs={"rosstat.scenario.kep2_product/extract.flake": flake.output("flake")},
            parameters={"dataset_id": "retained", "release_id": "v2"}, outputs=("view",))
        assert all("physical" not in task.task_id for task in plan.tasks)
        assert not any(task.operation_id in {"rosstat.command.tables.extract_workbook", "rosstat.command.tables.extract_kep2"} for task in plan.tasks)
        result = box.run(plan, timeout=30)
        assert result.outcome == "succeeded", errors(result)
        assert result.output("view").batch.dataset_id == "retained"


def test_population_canonical_mapping_keeps_dated_territory_and_stock_date():
    physical = extract_workbook(SourcePayload(_workbook_bytes()), series_id="rosstat.population_municipalities", issue_id="2024", asset_id="population_workbook")
    profile = ReviewedTableProfile("population.fixture", 1, physical.series_id, physical.source_identity,
        "reviewed deterministic population fixture", (_binding(),), "One dated municipality", _edition())
    with StrategyBox(capabilities=snapshot()) as box:
        mapped = box.invoke("rosstat.tables.map_reviewed_cells", inputs={"physical": physical}, parameters={"profile": profile}, timeout=15)
        assert mapped.outcome == "succeeded", errors(mapped)
        flake = mapped.output("flake")
        assert flake.values[0].value == Decimal(123)
        assert flake.values[0].period_kind == "as_of"
        integrated = box.invoke("rosstat.integration.integrate", inputs={"flakes": (flake,)},
            parameters={"dataset_id": "municipal", "release_id": "2024"}, timeout=15)
        assert integrated.outcome == "succeeded", errors(integrated)
        row, = integrated.output("dataset").batch.observations
        assert row.period.kind == "as_of" and row.period.as_of == date(2024, 1, 1)
        assert row.subject.id == "01000000" and row.perimeter == "municipality-a"
        invalid = box.invoke("rosstat.tables.map_reviewed_cells", inputs={"physical": physical},
            parameters={"profile": replace(profile, territory_edition=None)}, timeout=15)
        assert invalid.outcome == "failed"
        assert "rosstat.population_territory_reference_required" in errors(invalid)


def test_document_canonical_structure_is_required_for_reviewed_cells():
    payload = SourcePayload(b"%PDF fixture", "application/pdf")
    document = DocumentExtract("rosstat.socioeconomic_russia", "2024-01", "report", payload.identity, "pdf", "document.blocks.v1", 1,
        (DocumentBlock(0, "page", "Indicator|January|Value\nTrade|2024-01|100,2", 1, (), "page:1"),),
        (UsedInputReceipt.for_payload(payload, "source"),), SnapshotCoverage("partial", "Only page text"))
    binding = CellBinding("trade:R2C3", "trade", "Trade", "RUB", "billion rubles", "flow", "monthly",
        date(2024, 1, 1), date(2024, 1, 31), "iso3166-1", "RU", scale=Decimal(10)**9,
        block_id="trade", row=2, column=3)
    profile = ReviewedTableProfile("report.fixture", 1, document.series_id, payload.identity, "reviewed exact fixture", (binding,), "One reviewed table")
    layout = ReviewedDocumentLayout("layout.fixture", 1, payload.identity, "reviewed exact fixture", (DocumentTableRegion(0, "trade", 1, 2, 3, separator="|"),))
    with StrategyBox(capabilities=snapshot()) as box:
        unstructured = box.invoke("rosstat.tables.map_reviewed_cells", inputs={"physical": document}, parameters={"profile": profile}, timeout=15)
        assert unstructured.outcome == "failed"
        structured = box.invoke("rosstat.tables.structure_document", inputs={"document": document}, parameters={"layout": layout}, timeout=15)
        assert structured.outcome in {"succeeded", "partial"}, errors(structured)
        mapped = box.invoke("rosstat.tables.map_reviewed_cells", inputs={"physical": structured.output("document")}, parameters={"profile": profile}, timeout=15)
        assert mapped.outcome == "succeeded", errors(mapped)
        assert mapped.output("flake").values[0].value == Decimal("100.2")
        assert mapped.output("flake").values[0].scale == Decimal(10)**9


def test_regional_archive_recipe_keeps_container_and_member_evidence():
    from io import BytesIO
    from zipfile import ZipFile
    from stratbox.shared.source_publications import SourceAssetIdentity
    member_bytes = _workbook_bytes()
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("tables/reviewed.xlsx", member_bytes)
        archive.writestr("notes.txt", "Unselected source evidence")
    identity = SourceAssetIdentity("rosstat.socioeconomic_regions", "2024-01", "regional_archive")
    payload = SourcePayload(stream.getvalue(), "application/zip", identity.source_id)
    physical = extract_workbook(SourcePayload(member_bytes, source_id=identity.source_id),
        series_id=identity.series_id, issue_id=identity.issue_id, asset_id=identity.asset_id)
    binding = _binding(geography_namespace="iso3166-1", geography_id="RU", dimensions=(), perimeter="publisher_scope")
    profile = ReviewedTableProfile("regional.fixture", 1, identity.series_id, physical.source_identity,
        "reviewed archive fixture", (binding,), "One explicitly selected member")
    with StrategyBox(capabilities=snapshot()) as box:
        plan = box.prepare_goal("source.product", selection={"source_id": identity.series_id, "representation": "zip"},
            inputs={"payload": payload}, parameters={"issue_id": identity.issue_id, "asset_id": identity.asset_id,
                "member": "tables/reviewed.xlsx", "profile": profile, "dataset_id": "regional", "release_id": "v1"})
        result = box.run(plan, timeout=30)
        assert result.outcome == "succeeded", errors(result)
        flake = result.output("flake")
        receipt = next(receipt for receipt in flake.lineage if receipt.role == "archive_member")
        assert receipt.container == payload.identity and receipt.member == "tables/reviewed.xlsx"
        assert receipt.identity == physical.source_identity
        assert result.output("representation").data


def test_extract_goal_stops_before_integration_and_render(native_workbook):
    with StrategyBox(capabilities=snapshot()) as box:
        plan = box.prepare_goal("source.extract", selection={"source_id": "rosstat.short_term_indicators", "representation": "xlsx"},
            inputs={"payload": SourcePayload(native_workbook)}, parameters={"issue_id": "2025-01", "asset_id": "main_workbook"})
        assert {task.operation_id for task in plan.tasks if task.operation_id} == {
            "rosstat.command.tables.extract_workbook", "rosstat.command.tables.extract_kep2"}
        result = box.run(plan, timeout=30)
        assert result.outcome == "succeeded", errors(result)
        assert len({row.indicator_id for row in result.output("flake").values}) == 11


class Publisher:
    """Deterministic publisher transport for command-level effect assertions."""
    def __init__(self, body):
        self.body, self.requests = body, []
    def exchange(self, request, *, cancelled=None):
        from datetime import datetime, timezone
        from stratbox.core.network import HttpResponse
        self.requests.append(request)
        return HttpResponse(200, self.body, {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            datetime(2026, 11, 25, tzinfo=timezone.utc), "https://rosstat.gov.ru")
    def exchange_into(self, request, sink, *, cancelled=None):
        from dataclasses import replace
        from stratbox.core.network import HttpStreamResponse
        from stratbox.shared.identity import ByteIdentity
        response = self.exchange(request, cancelled=cancelled)
        sink.write(self.body)
        return HttpStreamResponse(replace(response, body=b""), ByteIdentity.of(self.body))


def test_asset_admission_transfer_and_preservation_are_explicit_command_effects(native_workbook, tmp_path):
    from stratbox.core.operations.source.original_definitions import OriginalDestination
    from stratbox.core.storage.filestore import LocalFileStore
    series = "rosstat.short_term_indicators"
    html = SourcePayload(b'<a href="/storage/mediabank/2026-08.xlsx">August2026</a>', "text/html", series + ".index", charset="utf-8")
    provider = Publisher(native_workbook)
    with StrategyBox(capabilities=snapshot(), providers={"http": provider, "output_filestore": LocalFileStore(str(tmp_path))}) as box:
        discovered = box.invoke("rosstat.publications.discover", inputs={"index": html}, parameters={"series_id": series}, timeout=15)
        assert discovered.outcome == "succeeded", errors(discovered)
        asset, = discovered.output("index").qualified_assets
        acquired = box.invoke("rosstat.publications.acquire", inputs={"asset": asset}, timeout=15)
        assert acquired.outcome == "succeeded", errors(acquired)
        assert acquired.output("payload").data == native_workbook
        assert acquired.output("acquired").detected_format == "xlsx"
        assert {task.operation_id for task in acquired.tasks if task.operation_id} == {
            "rosstat.command.asset.admit", "rosstat.command.asset.receive", "rosstat.command.asset.verify"}
        captured = box.invoke("rosstat.publications.acquire_to_store", inputs={"asset": asset},
            parameters={"destination": OriginalDestination("original.xlsx")}, timeout=15)
        assert captured.outcome == "succeeded", errors(captured)
        assert captured.output("stored").source.storage.status == "stored"
        assert (tmp_path / "original.xlsx").read_bytes() == native_workbook
        assert any(effect.kind == "storage.write" and effect.state == "confirmed"
            for value in captured.results.values() for effect in value.effects)
        count = len(provider.requests)
        rejected = box.invoke("rosstat.publications.acquire", inputs={"asset": replace(asset, url="https://invalid.example/original.xlsx")}, timeout=15)
        assert rejected.outcome == "failed" and len(provider.requests) == count
        assert "rosstat.asset_url_forbidden" in errors(rejected)
