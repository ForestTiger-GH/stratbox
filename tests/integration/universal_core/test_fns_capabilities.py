"""FNS scientific routes through the canonical command executor."""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import json

import pytest

from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.domains.fns.capabilities import contribution, dispositions, stage_matrix
from stratbox.domains.fns.publications.contracts import ReleaseContext
from stratbox.sdk import StrategyBox
from stratbox.shared.evidence import SourcePayload

from source_fixtures import FORM_EPOCHS, encoded, fixture, form_workbook

DAY = date(2026, 11, 10)


def context(series="fns.sme", day=DAY):
    return ReleaseContext(series, day.isoformat(), day, published_on=day)


@pytest.fixture
def catalog():
    builtins = catalog_snapshot()
    return builtins if any(item.capability_id == "fns.sme.process" for item in builtins.definitions) else builtins.overlay(contribution())


def success(result):
    assert result.outcome == "succeeded", [(name, value.diagnostics) for name, value in result.results.items()]
    return result


def invoke(box, name, inputs, parameters=None, **options):
    return success(box.invoke(name, inputs=inputs, parameters=parameters, timeout=20, **options))


def test_dispositions_cover_both_sources_and_useful_conveniences_have_correct_kinds(catalog):
    records = dispositions()
    assert len(records) == 62 and len({item["original_id"] for item in records}) == 62
    assert len(stage_matrix()) == 2
    for item in records:
        assert catalog.definition(item["capability_id"]).kind == item["kind"]
    assert catalog.definition("fns.sme.process").kind == "scenario"
    assert catalog.definition("fns.1yur.extract").kind == "operation"
    assert all("operations" not in item.implementation_ref for item in contribution().definitions if item.kind == "command")
    assert len(contribution().profiles) == 8


def test_command_identities_include_the_scientific_algorithms_and_codecs():
    from stratbox.core.execution.methods import algorithm_fingerprints
    actual = algorithm_fingerprints(tuple("stratbox.domains.fns.capability_commands:" + name
        for name in ("project", "align", "snapshot", "replay", "acquire")))
    assert {
        "stratbox.domains.fns.tables.sme.projection:project_counts",
        "stratbox.domains.fns.tables.legal_entities.projection:project_reported",
        "stratbox.domains.fns.integration.sme.alignment:align",
        "stratbox.domains.fns.integration.legal_entities.alignment:align",
        "stratbox.domains.fns.tables.sme.snapshots:flake_snapshot",
        "stratbox.domains.fns.tables.legal_entities.snapshots:flake_snapshot",
        "stratbox.domains.fns.integration.snapshots:dataset_snapshot",
        "stratbox.domains.fns.publications.sme.access:acquire_source",
        "stratbox.domains.fns.publications.legal_entities.access:acquire_source",
    } <= actual.keys()


def test_sme_commands_preserve_literal_types_and_independent_projections(catalog):
    source = fixture()
    for row in source:
        if row["cnt_level"] == 1:
            row.update(cnt_total=11, cnt_ul_total=6, cnt_ip_total=5, cnt_ul_micro=4,
                cnt_ul_mini=1, cnt_ul_normal=1, cnt_ip_micro=3, cnt_ip_mini=1, cnt_ip_normal=1)
    source[0]["unknown"] = {"nested": [True, None, "01"]}
    raw = encoded(source).replace(b'"unknown": {', b'"unknown": {"number": 1.2300e+2, ', 1)
    with StrategyBox(capabilities=catalog) as box:
        result = invoke(box, "fns.sme.process", {"payload": SourcePayload(raw), "release": context()})
        flake, projection, dataset = (result.output(name) for name in ("flake", "projection", "dataset"))
        unknown = next(item for item in flake.records[0].fields if item.name == "unknown")
        assert unknown.kind == "object" and "1.2300e+2" in unknown.raw_token
        assert unknown.value["number"] == Decimal("123.00")
        assert "source.unmapped_field" in projection.qualifications
        assert {item.subject.namespace for item in dataset.batch.observations} == {
            "fns.ssrf", "fns.sme.country", "fns.sme.federal_district"}
        readable = invoke(box, "fns.sme.readable", {"flake": flake}).output("readable")
        assert b"1.2300e+2" in readable.data
        plan = box.prepare("fns.sme.process", outputs=("representation",),
            supplied_outputs={"fns.sme.process/view.view": result.output("view")})
        assert [task.operation_id for task in plan.tasks if task.operation_id] == ["fns.sme.command.render"]
        assert success(box.run(plan, timeout=20)).output("representation") == result.output("representation")


def test_fns_profiles_and_mapping_references_are_pinned_by_preparation(catalog):
    with StrategyBox(capabilities=catalog) as box:
        plan = box.prepare("fns.sme.process", inputs={"payload": encoded(fixture()), "release": context()})
        binding = plan.selected_bindings["fns.sme.process/align"]
        assert binding["profile_id"] == "fns.sme.published-counts-alignment"
        assert binding["identities"]["reference:fns.sme.field-mapping"]
        assert plan.selected_bindings["fns.sme.process/extract"]["profile_id"] == "fns.sme.full-json"


def test_saved_layers_replay_without_reacquisition_or_decoding(catalog, monkeypatch):
    from stratbox.core.storage.datasets.codec import decode_table, encode_table, manifest_from
    from stratbox.shared.data.snapshots import DatasetSnapshot, manifest_value
    with StrategyBox(capabilities=catalog) as box:
        processed = invoke(box, "fns.sme.process", {"payload": encoded(fixture()), "release": context()})
        for layer in ("flake", "projection", "dataset", "view"):
            value = processed.output(layer)
            snapshot = invoke(box, "fns.sme." + layer + "_snapshot", {layer: value}).output("snapshot")
            portable = DatasetSnapshot(manifest_from(json.loads(json.dumps(manifest_value(snapshot.manifest)))),
                tuple((name, decode_table(encode_table(table))) for name, table in snapshot.tables))
            replayed = invoke(box, "fns.sme.read_" + layer + "_snapshot", {"snapshot": portable}).output(layer)
            assert replayed == value
        import stratbox.domains.fns.capability_commands as commands
        monkeypatch.setattr(commands, "extract", lambda *_: pytest.fail("retained view must skip extraction"))
        assert invoke(box, "fns.sme.render", {"view": processed.output("view")}).output("representation") == processed.output("representation")


def test_generic_dataset_query_connects_to_exact_fns_replay_and_validates_the_manifest(catalog):
    from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
    from stratbox.core.storage.datasets import MemoryDatasetStore
    from stratbox.shared.data.processing import DataContract
    generic = DataContract("dataset.snapshot", 1)
    for series in ("fns.sme", "fns.1yur"):
        for layer in ("flake", "projection", "dataset", "calculation", "view"):
            reader = catalog.definition(series + ".read_" + layer + "_snapshot")
            writer = catalog.definition(series + "." + layer + "_snapshot")
            assert reader.inputs["snapshot"].alternatives == (generic,)
            assert reader.inputs["snapshot"].schema == writer.outputs["snapshot"].schema
            assert not writer.outputs["snapshot"].alternatives
    store = MemoryDatasetStore(provider_id="fns.fixture", scope_id="stored")
    readback = ScenarioDefinition("fixture.fns_stored_replay", GraphBody((
        Call("read", "query.dataset", {"reference": InputRef("reference")}),
        Call("restore", "fns.sme.read_dataset_snapshot", {"snapshot": OutputRef("read")}),
    ), {"dataset": OutputRef("restore", "dataset")}),
        inputs={"reference": catalog.definition("query.dataset").inputs["reference"]},
        outputs=catalog.definition("fns.sme.read_dataset_snapshot").outputs)
    with StrategyBox(capabilities=catalog, providers={"dataset_writer": store, "dataset_reader": store}) as box:
        processed = invoke(box, "fns.sme.process", {"payload": encoded(fixture()), "release": context()})
        dataset = processed.output("dataset")
        snapshot = invoke(box, "fns.sme.dataset_snapshot", {"dataset": dataset}).output("snapshot")
        reference = invoke(box, "ingest.observations", {"value": snapshot}).output("value")
        result = success(box.run(box.prepare(readback, inputs={"reference": reference}), timeout=20))
        assert result.output("dataset") == dataset
        # A generic storage envelope cannot turn a flake into an integrated
        # dataset: the exact replay codec still admits the embedded manifest.
        physical = invoke(box, "fns.sme.flake_snapshot", {"flake": processed.output("flake")}).output("snapshot")
        wrong_layer = invoke(box, "ingest.observations", {"value": physical}).output("value")
        rejected = box.run(box.prepare(readback, inputs={"reference": wrong_layer}), timeout=20)
        assert rejected.outcome == "failed"
        assert any(diagnostic.code == "fns.snapshot_layer_mismatch"
            for value in rejected.results.values() for diagnostic in value.diagnostics)


@pytest.mark.parametrize("day,epoch,indicators,kinds", FORM_EPOCHS, ids=[item[1] for item in FORM_EPOCHS])
def test_historical_1yur_epochs_decode_and_align_through_command_bodies(catalog, day, epoch, indicators, kinds):
    with StrategyBox(capabilities=catalog) as box:
        result = invoke(box, "fns.1yur.process", {"payload": form_workbook(indicators, kinds, legacy=epoch == "A"),
            "release": context("fns.1yur", day)})
        flake, dataset = result.output("flake"), result.output("dataset")
        assert flake.members and flake.members[0][1].format == ("xls" if epoch == "A" else "xlsx")
        assert json.loads(dataset.details_json)["epoch"] == epoch
        assert dataset.coverage.status == "partial"
        assert {item.perimeter for item in dataset.batch.observations} == {
            "published_national", "published_district", "published_territory"}
        assert "source.ceased_bankruptcy_period_basis_unresolved" in dataset.qualifications
        assert all(item.evidence_ref.startswith("member:main:sheet:") for item in result.output("projection").batch.observations)


def test_1yur_formula_evidence_survives_physical_snapshot(catalog):
    import openpyxl
    day, _, indicators, kinds = FORM_EPOCHS[-1]
    book = openpyxl.load_workbook(BytesIO(form_workbook(indicators, kinds)))
    note = book.create_sheet("Unselected evidence")
    note["B12"] = "source note"
    note["C12"] = "=1+1"
    stream = BytesIO()
    book.save(stream)
    with StrategyBox(capabilities=catalog) as box:
        flake = invoke(box, "fns.1yur.extract", {"payload": stream.getvalue(), "release": context("fns.1yur", day)}).output("flake")
        snapshot = invoke(box, "fns.1yur.flake_snapshot", {"flake": flake}).output("snapshot")
        replayed = invoke(box, "fns.1yur.read_flake_snapshot", {"snapshot": snapshot}).output("flake")
        note = next(sheet for sheet in replayed.members[0][1].sheets if sheet.name == "Unselected evidence")
        assert note.cell(12, 2).value == "source note" and note.cell(12, 3).formula == "1+1"


def test_native_csv_admission_preserves_partial_scope_and_enables_independent_calculation(catalog):
    with StrategyBox(capabilities=catalog) as box:
        parsed = invoke(box, "fns.sme.parse", {"payload": encoded(fixture()), "release": context()})
        representation = parsed.output("representation")
        first = invoke(box, "fns.sme.read_representation", {"payload": SourcePayload(representation.data, "text/csv"),
            "release": context()}).output("dataset")
        second = invoke(box, "fns.sme.read_representation", {"payload": SourcePayload(representation.data, "text/csv"),
            "release": context(day=date(2026, 12, 10))}).output("dataset")
        assert first.source_identity == representation.identity
        assert first.coverage.status == "partial"
        assert "source.physical_original_unavailable" in first.qualifications
        assert {item.subject.namespace for item in first.batch.observations} == {"fns.ssrf"}
        change = invoke(box, "fns.sme.calculate_changes", {"before": first, "after": second}, {"metric_ids": ("total",)}).output("calculation")
        assert change.batch.observations and {item.value for item in change.batch.observations} == {0}
        assert "calculation.net_stock_change_is_not_entries_or_exits" in change.qualifications


def test_source_date_and_family_rejections_have_domain_diagnostics(catalog):
    with StrategyBox(capabilities=catalog) as box:
        flake = invoke(box, "fns.sme.extract", {"payload": encoded(fixture(date(2026, 11, 9))), "release": context()}).output("flake")
        report = invoke(box, "fns.sme.validate", {"flake": flake}).output("report")
        assert not report.valid
        rejected = box.invoke("fns.sme.project", inputs={"flake": flake}, timeout=20)
        assert rejected.outcome == "failed"
        assert next(iter(rejected.results.values())).diagnostics[0].code == "source.source_date_mismatch"
        snapshot = invoke(box, "fns.sme.flake_snapshot", {"flake": flake}).output("snapshot")
        rejected = box.invoke("fns.1yur.read_flake_snapshot", inputs={"snapshot": snapshot}, timeout=20)
        assert rejected.outcome == "failed"


def test_capture_stamp_remains_independent_of_observation_and_publication_dates(catalog):
    from stratbox.core.network import HttpResponse
    observed = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    class Transport:
        def exchange(self, request, *, cancelled=None):
            assert request.method == "POST" and request.form_fields["statDate"]
            return HttpResponse(200, encoded(fixture()), {"Content-Type": "application/json"}, observed,
                "https://rmsp.nalog.ru")
    with StrategyBox(capabilities=catalog, providers={"http": Transport()}) as box:
        result = invoke(box, "fns.sme.capture_full", {"release": context()})
        assert result.output("original").identity == result.output("acquisition").identity
        assert result.output("flake").context.captured_at == observed
        assert result.output("flake").context.observation_date == result.output("flake").context.published_on == DAY


def test_rar_provider_is_admitted_only_for_the_rar_branch(catalog):
    from contextlib import contextmanager
    from stratbox.core.formats.archives.members import ArchiveMember
    day, _, indicators, kinds = FORM_EPOCHS[-1]
    workbook = form_workbook(indicators, kinds)
    calls = []
    class Contents:
        def members(self):
            return (ArchiveMember("release_I.xlsx", len(workbook)),)
        @contextmanager
        def open(self, name):
            assert name == "release_I.xlsx"
            yield BytesIO(workbook)
    class Decoder:
        @contextmanager
        def open(self, data):
            calls.append(data)
            yield Contents()
    with StrategyBox(capabilities=catalog, providers={"archive_decoder": Decoder()}) as box:
        flake = invoke(box, "fns.1yur.extract", {"payload": b"Rar!controlled", "release": context("fns.1yur", day)}).output("flake")
        assert flake.container_format == "rar" and calls == [b"Rar!controlled"]
        assert flake.members[0][0] == "release_I.xlsx"
        assert flake.lineage[1].container == flake.source_identity
    with StrategyBox(capabilities=catalog) as box:
        rejected = box.invoke("fns.1yur.extract", inputs={"payload": b"Rar!controlled", "release": context("fns.1yur", day)}, timeout=20)
        assert rejected.outcome == "failed"
        assert any(diagnostic.code == "provider.capability_missing"
            for value in rejected.results.values() for diagnostic in value.diagnostics)
        standalone = invoke(box, "fns.1yur.extract", {"payload": workbook, "release": context("fns.1yur", day)})
        assert standalone.output("flake").container_format == "standalone"
