"""Canonical report routes preserve the same physical and semantic evidence."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.frank_rg.capabilities import contribution, dispositions, stage_matrix
from stratbox.domains.frank_rg.publications.catalog import all_sources
from stratbox.domains.frank_rg.publications.contracts import ReportPeriod
from stratbox.domains.frank_rg.tables.contracts import CellBinding, SemanticProfile
from stratbox.domains.frank_rg.tables.flakes import profile_identity
from stratbox.domains.frank_rg.tables.layouts import CellAnchor, LayoutBinding, LayoutProfile, bind_layout
from stratbox.sdk import StrategyBox
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
from stratbox.shared.evidence import SourcePayload


def catalog():
    item = contribution()
    return CatalogSnapshot(item.definitions, item.methods, item.profiles, item.groups, item.recipes)


def material(value="123.456789012345678901234567890", unit="RUB million"):
    book = Workbook()
    sheet = book.active
    sheet.title = "Fixture"
    sheet.append(("Bank", unit))
    sheet.append(("Fixture bank", value))
    sheet.append(("Missing bank", "—"))
    sheet.merge_cells("D1:E1")
    result = BytesIO()
    book.save(result)
    return SourcePayload(result.getvalue())


def accepted(box, identifier, **options):
    result = box.invoke(identifier, timeout=15, **options)
    assert result.outcome == "succeeded", [(key, value.diagnostics) for key, value in result.results.items()]
    return result


def captured(box, source_id, payload):
    return accepted(box, "frg.capture", inputs={"payload": payload}, parameters={
        "source_id": source_id, "period": ReportPeriod(date(2026, 5, 1),
            1 if source_id.endswith("issuance_weekly") else None), "format": "xlsx"}).output("report")


def bound(extract):
    return SemanticProfile(extract.series_id, "fixture.frg.amount", 1, extract.source_identity, (
        CellBinding("Fixture", 2, 2, SubjectRef("bank", "fixture"),
            MetricRef("fixture.amount", "RUB", "stock", "fixture.v1", Decimal(1000000)),
            PeriodRef("as_of", as_of=date(2026, 4, 30)), "fixture_population"),
        CellBinding("Fixture", 3, 2, SubjectRef("bank", "missing"),
            MetricRef("fixture.amount", "RUB", "stock", "fixture.v1", Decimal(1000000)),
            PeriodRef("as_of", as_of=date(2026, 4, 30)), "fixture_population"),
    ))


def test_complete_callable_scope_is_metadata_only_and_semantic_evidence_remains_qualified():
    snapshot = catalog()
    assert len(dispositions()) == 32
    assert {item["source_id"] for item in stage_matrix()} == set(all_sources())
    assert len(snapshot.groups) == 14 and len(snapshot.profiles) == 8
    assert snapshot.definition("frg.scan").kind == "scenario"
    assert {step.capability_id for step in snapshot.definition("frg.scan").body.steps} == {
        "frg.discover", "frg.inspect", "frg.select", "frg.catalog.compose"}
    assert all(item["publisher_layouts_verified"] is False for item in stage_matrix())
    assert all(snapshot.definition(item["capability_id"]) for item in dispositions())


@pytest.mark.parametrize("source_id", all_sources())
def test_all_series_run_product_and_portable_replay_through_canonical_session(source_id, monkeypatch):
    from stratbox.domains.frank_rg.operations import handlers, pipeline_handlers, housekeeping
    def forbidden(*args, **kwargs):
        raise AssertionError("canonical command started a nested runner")
    for module in (handlers, pipeline_handlers, housekeeping):
        monkeypatch.setattr(module, "run", forbidden)
    payload = material()
    with StrategyBox(capabilities=catalog()) as box:
        report = captured(box, source_id, payload)
        extract = accepted(box, "frg.extract", inputs={"report": report}).output("value")
        assert extract.sheets[0].merged_ranges == ("D1:E1",)
        assert extract.source_identity == payload.identity
        profile = bound(extract)
        product = accepted(box, "frg.report.product", inputs={"report": report, "profile": profile},
            parameters={"dataset_id": source_id + ".analysis", "release_id": "edition1", "view_id": "fixture"})
        batch = product.output("observations")
        assert batch.observations[0].value == Decimal("123.456789012345678901234567890")
        assert batch.observations[1].value_status == "dash"
        assert batch.source_uses[0].coordinate.material_identity == payload.identity
        assert b"123.456789012345678901234567890" in product.output("representation").data
        snapshot = accepted(box, "frg.flake_snapshot", inputs={"flake": product.output("flake")}).output("snapshot")
        replayed = accepted(box, "frg.read_flake", inputs={"snapshot": snapshot}).output("value")
        assert replayed == product.output("flake")
        # An existing extract is independently useful and causes no reacquire.
        isolated = accepted(box, "frg.build_flake", inputs={"extract": extract, "profile": profile}).output("value")
        assert isolated == replayed


def test_reusable_layout_requires_exact_scope_geometry_anchors_and_explicit_periods():
    with StrategyBox(capabilities=catalog()) as box:
        extract = accepted(box, "frg.extract", inputs={"report": captured(box, "frg.express.issuance", material())}).output("value")
        profile = bound(extract)
        layout = LayoutProfile(extract.series_id, "fixture.layout", 1, ("xlsx",),
            tuple((sheet.name, sheet.rows, sheet.columns) for sheet in extract.sheets),
            (CellAnchor("Fixture", 1, 1, "Bank"), CellAnchor("Fixture", 1, 2, "RUB million")),
            tuple(LayoutBinding(cell, "stock") for cell in profile.bindings),
            (extract.source_identity,), "synthetic_fixture_review_only")
        periods = {"stock": PeriodRef("as_of", as_of=date(2026, 4, 30))}
        actual = accepted(box, "frg.bind_layout", inputs={"extract": extract, "layout": layout}, parameters={"periods": periods}).output("profile")
        assert actual.layout_identity == layout.identity
        assert actual.original_identity == extract.source_identity
        changed = accepted(box, "frg.extract", inputs={"report": captured(box, "frg.express.issuance", material("456"))}).output("value")
        rebound = bind_layout(changed, layout, periods=periods)
        assert rebound.original_identity == changed.source_identity != actual.original_identity
        assert profile_identity(rebound) != profile_identity(actual)
        unit_changed = accepted(box, "frg.extract", inputs={"report": captured(box, "frg.express.issuance", material(unit="USD million"))}).output("value")
        with pytest.raises(ValueError, match="anchor_mismatch"):
            bind_layout(unit_changed, layout, periods=periods)
        with pytest.raises(ValueError, match="periods_required"):
            bind_layout(extract, layout, periods={})
        altered = replace(layout, review_qualification="changed_review")
        assert profile_identity(bind_layout(extract, altered, periods=periods)) != profile_identity(actual)
        flake = accepted(box, "frg.build_flake", inputs={"extract": extract, "profile": actual}).output("value")
        assert "externally_reviewed_layout" in flake.qualifications
        assert "synthetic_fixture_review_only" in flake.qualifications


def test_scan_cleanup_and_archive_keep_independent_effect_boundaries(tmp_path):
    filename = "2026-05-01_Экспресс выдачи.xlsx"
    # A supplier filename is recognized independently of storage preparation.
    supplier = "FRG. Экспресс-мониторинг рынка выдачи 2026-05-01.xlsx"
    store = LocalFileStore(str(tmp_path))
    store.write_bytes(supplier, b"publisher original")
    with StrategyBox(capabilities=catalog(), providers={"filestore": store}) as box:
        scan = accepted(box, "frg.scan", parameters={"directory": "."})
        assert scan.output("catalog").inventory == scan.output("inventory")
        assert store.read_bytes(supplier) == b"publisher original"
        plan = accepted(box, "frg.plan_cleanup", parameters={"directory": ".", "delete_others": False}).output("plan")
        assert not store.exists(filename)
        archive = accepted(box, "frg.prepare_archive", inputs={"plan": plan}).output("archive")
        assert archive.media_type == "application/zip"
        assert not store.exists(filename)
        result = accepted(box, "frg.apply_cleanup", inputs={"plan": plan},
            parameters={"authorized_directory": ".", "expected_sha256": plan.identity.sha256})
        assert all(receipt.state == "confirmed" for receipt in result.output("receipts"))
        assert store.exists(supplier)
        assert store.read_bytes(plan.actions[0].destination) == b"publisher original"
        assert any(effect.state == "confirmed" for value in result.results.values() for effect in value.effects)


def test_stream_archive_reconciles_unknown_commit_without_repeating_extraction(tmp_path):
    from contextlib import contextmanager
    class LostAckStore(LocalFileStore):
        @contextmanager
        def stage_write(self, destination):
            with super().stage_write(destination) as stage:
                class CommitThenLoseAck:
                    stream = stage.stream
                    def commit(self, mode, revision):
                        assert stage.commit(mode, revision) is True
                        raise TimeoutError("lost after actual commit")
                yield CommitThenLoseAck()
    source = LocalFileStore(str(tmp_path / "source"))
    source.write_bytes("FRG. Экспресс-мониторинг рынка выдачи 2026-05-01.xlsx", b"exact original")
    with StrategyBox(capabilities=catalog(), providers={"filestore": source}) as box:
        plan = accepted(box, "frg.plan_cleanup", parameters={"directory": "."}).output("plan")
    output_path = tmp_path / "output"
    with StrategyBox(capabilities=catalog(), providers={"filestore": source, "output_filestore": LostAckStore(str(output_path))}) as box:
        lost = box.invoke("frg.prepare_archive_to_store", inputs={"plan": plan}, parameters={"destination": "reports.zip"}, timeout=15)
        assert lost.outcome == "unknown"
        assert any(effect.state == "unknown" for value in lost.results.values() for effect in value.effects)
        physical = next(iter(lost.results.values()))
        from stratbox.core.formats.archives.store import PathArchiveReceipt
        assert isinstance(physical.value, PathArchiveReceipt)
        assert physical.value.storage.status == "unknown"
        assert physical.value.identity == LocalFileStore(str(output_path)).inspect_file("reports.zip").identity
        assert "archive" not in lost.outputs
        assert not any(item.code == "acceptance.coherent_outputs_missing" for item in physical.diagnostics)
    destination = LocalFileStore(str(output_path))
    committed = destination.inspect_file("reports.zip")
    with StrategyBox(capabilities=catalog(), providers={"filestore": source, "output_filestore": destination}) as box:
        replay = accepted(box, "frg.prepare_archive_to_store", inputs={"plan": plan}, parameters={"destination": "reports.zip"}).output("archive")
        assert replay.storage.status == "already_present"
        assert replay.identity == committed.identity


def test_shared_preserve_ingest_query_and_publish_routes_accept_actual_frank_types(tmp_path):
    from stratbox.capabilities.manifest import catalog_snapshot
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    from stratbox.shared.data.observation_snapshots import observations_from_snapshot
    import json
    snapshot = catalog_snapshot().overlay(contribution())
    files = LocalFileStore(str(tmp_path))
    datasets = MemoryDatasetStore(provider_id="frank-fixture", scope_id="shared-routes")
    payload = material()
    with StrategyBox(capabilities=snapshot, providers={"output_filestore": files,
            "dataset_writer": datasets, "dataset_reader": datasets}) as box:
        report = captured(box, "frg.express.issuance", payload)
        original = accepted(box, "preserve.material", inputs={"material": report.payload},
            parameters={"destination": "original.xlsx"}).output("receipt")
        assert original.identity == payload.identity
        extract = accepted(box, "frg.extract", inputs={"report": report}).output("value")
        retained = accepted(box, "frg.extract_snapshot", inputs={"extract": extract}).output("snapshot")
        assert accepted(box, "frg.read_extract", inputs={"snapshot": retained}).output("value") == extract
        product = accepted(box, "frg.report.product", inputs={"report": report, "profile": bound(extract)},
            parameters={"dataset_id": "frank.integrated", "release_id": "edition1", "view_id": "fixture"})
        batch = product.output("observations")
        reference = accepted(box, "ingest.observations", inputs={"value": batch}).output("value")
        stored = accepted(box, "query.dataset", inputs={"reference": reference}).output("value")
        assert observations_from_snapshot(stored) == batch
        receipt = accepted(box, "preserve.material", inputs={"material": product.output("representation")},
            parameters={"destination": "product.csv"}).output("receipt")
        released = accepted(box, "publish.release", inputs={"receipts": (original, receipt)}, parameters={
            "release_id": "frank.fixture.release", "destination": "release.json",
            "members": ("original", "product"), "input_versions": {"integrated": reference.identity.sha256},
            "member_versions": {"original": {"integrated": reference.identity.sha256},
                "product": {"integrated": reference.identity.sha256}},
            "expected_members": {"original": original.identity.sha256, "product": receipt.identity.sha256}})
        manifest = json.loads(released.output("manifest").data)
        assert manifest["input_versions"] == {"integrated": reference.identity.sha256}
        assert {item["name"] for item in manifest["members"]} == {"original", "product"}
        assert files.read_bytes("original.xlsx") == payload.data
        assert files.read_bytes("release.json") == released.output("manifest").data
    rows = stage_matrix()
    assert all({"preserve", "read_extract", "ingest", "publish"} <= row["stages"].keys() for row in rows)


def test_stored_query_flows_to_exact_domain_replay_and_rejects_wrong_manifest():
    from stratbox.capabilities.manifest import catalog_snapshot
    from stratbox.capabilities.catalog import CatalogContribution
    from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    snapshot = catalog_snapshot().overlay(contribution())
    stores = MemoryDatasetStore(provider_id="frank-replay", scope_id="shared-snapshot")
    scenarios = []
    for name in ("extract", "flake", "observations", "view"):
        operation = "frg.read_" + name
        scenarios.append(ScenarioDefinition("frg.fixture.replay_" + name, GraphBody((
            Call("query", "query.dataset", {"reference": InputRef("reference")}),
            Call("restore", operation, {"snapshot": OutputRef("query")}),
        ), {"value": OutputRef("restore")}),
            inputs={"reference": snapshot.definition("query.dataset").inputs["reference"]},
            outputs={"value": snapshot.definition(operation).outputs["value"]}))
    snapshot = snapshot.overlay(CatalogContribution(definitions=tuple(scenarios)))
    with StrategyBox(capabilities=snapshot, providers={"dataset_writer": stores, "dataset_reader": stores}) as box:
        report = captured(box, "frg.express.issuance", material())
        extract = accepted(box, "frg.extract", inputs={"report": report}).output("value")
        product = accepted(box, "frg.report.product", inputs={"report": report, "profile": bound(extract)},
            parameters={"dataset_id": "frank.replay", "release_id": "edition1", "view_id": "fixture"})
        values = {"extract": extract, "flake": product.output("flake"),
            "observations": product.output("observations"), "view": product.output("view")}
        reference = None
        for name, value in values.items():
            operation, field = {
                "extract": ("frg.extract_snapshot", "extract"),
                "flake": ("frg.flake_snapshot", "flake"),
                "observations": ("frg.observation_snapshot", "batch"),
                "view": ("frg.view_snapshot", "view"),
            }[name]
            retained = accepted(box, operation, inputs={field: value}, parameters={
                "dataset_id": "frank.snapshot." + name, "version_id": "edition1"}).output("snapshot")
            reference = accepted(box, "ingest.observations", inputs={"value": retained}).output("value")
            restored = accepted(box, "frg.fixture.replay_" + name, inputs={"reference": reference}).output("value")
            assert restored == value
        # The generic carrier does not erase the exact retained manifest type.
        rejected = box.invoke("frg.fixture.replay_extract", inputs={"reference": reference}, timeout=15)
        assert rejected.outcome == "failed"
        assert any(item.code == "workbook.snapshot_invalid" for result in rejected.results.values() for item in result.diagnostics)

