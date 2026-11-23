"""FNS semantic boundaries, source retention, offline replay and historical safeguards."""
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import json

import pytest

from stratbox.core.execution import ExecutionBudget, ExecutionContext
from stratbox.core.formats.archives.members import zip_bytes
from stratbox.core.storage.datasets.codec import decode_table, encode_table, manifest_from
from stratbox.shared.data.snapshots import DatasetSnapshot, manifest_value
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.fns.operations import legal_entities, sme
from stratbox.domains.fns.publications.catalog import all_sources, families

from source_fixtures import FORM_EPOCHS, encoded, fixture, form_workbook

SME_DAY = date(2026, 11, 10)


def success(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def context(series, day):
    return sme.ReleaseContext(series, day.isoformat(), day,
        published_on=day, captured_at=datetime(2026, 11, 20, 12, tzinfo=timezone.utc))


def retained(snapshot):
    """Cross the actual neutral table/manifest serialization boundary."""
    manifest = manifest_from(json.loads(json.dumps(manifest_value(snapshot.manifest))))
    return DatasetSnapshot(manifest, tuple((name, decode_table(encode_table(table))) for name, table in snapshot.tables))


def sme_source(day=SME_DAY, *, increment=0):
    source = fixture(day)
    for row in source:
        if row["cnt_level"] == 1:
            row.update(cnt_total=11, cnt_ul_total=6, cnt_ip_total=5, cnt_ul_micro=4,
                cnt_ul_mini=1, cnt_ul_normal=1, cnt_ip_micro=3, cnt_ip_mini=1, cnt_ip_normal=1)
        if row["cnt_level"] == 0 and row["ssrf"] == "01":
            row["cnt_total"] += increment
            row["cnt_ul_total"] += increment
            row["cnt_ul_micro"] += increment
    return source


def sme_dataset(day=SME_DAY, *, increment=0):
    flake = success(sme.extract(sme.ExtractRequest(SourcePayload(encoded(sme_source(day, increment=increment))), context("fns.sme", day))))
    projection = success(sme.project(sme.FlakeRequest(flake)))
    return success(sme.align(sme.ProjectionRequest(projection)))


def test_registry_has_two_meaningful_families_and_complete_real_bindings():
    from stratbox.domains.fns._registration import REGISTRATION
    from stratbox.domains.fns.operations.source_catalog import source_cards
    assert families() == ("fns.sme", "fns.legal_entities")
    assert {value.series_id for value in all_sources()} == {"fns.sme", "fns.1yur"}
    assert REGISTRATION.owner_id == "fns"
    references = {item.operation_id for item in REGISTRATION.operations}
    for card in source_cards():
        for operation in card.operations:
            if operation.state != "delegated":
                assert operation.operation_id in references
    assert not sme.FLAKE_SNAPSHOT.processing.stages
    assert sme.FLAKE_SNAPSHOT.processing.function.value == "encode"
    assert sme.READ_FLAKE_SNAPSHOT.processing.function.value == "replay"


def test_sme_full_json_retains_all_levels_fields_native_types_and_raw_tokens():
    source = sme_source()
    source[0]["future_field"] = {"nested": [1, True, None, "01"]}
    raw = encoded(source).replace(b'"future_field": {', b'"future_field": {"decimal": 1.2300e+2, ', 1)
    flake = success(sme.extract(sme.ExtractRequest(SourcePayload(raw), context("fns.sme", SME_DAY))))
    assert len(flake.records) == len(source)
    assert {record.values()["cnt_level"] for record in flake.records} == {0, 1, 2}
    extra = next(field for field in flake.records[0].fields if field.name == "future_field")
    assert extra.kind == "object" and "1.2300e+2" in extra.raw_token
    assert extra.value["decimal"] == Decimal("123.00")
    snapshot = success(sme.flake_snapshot(sme.FlakeRequest(flake)))
    replay = success(sme.read_flake_snapshot(sme.SnapshotRequest(retained(snapshot))))
    assert replay == flake and replay.identity == flake.identity
    assert replay.context.published_on == SME_DAY
    assert replay.context.captured_at.hour == 12
    assert {dimension.name for dimension in replay.coverage.dimensions} == {"fields", "geographic_levels"}
    readable = success(sme.readable(sme.FlakeRequest(replay)))
    assert b"1.2300e+2" in readable.data
    projected = success(sme.project(sme.FlakeRequest(replay)))
    assert "source.unmapped_field" in projected.qualifications
    assert any(item.source_field.endswith(":future_field") and item.target_field is None for item in projected.dispositions)
    assert {item.subject.namespace for item in projected.batch.observations} == {
        "fns.ssrf", "fns.sme.country", "fns.sme.federal_district"}
    assert {"cnt_ul_total", "cnt_ip_total"} <= {item.metric.id for item in projected.batch.observations}


def test_sme_native_integer_and_decimal_string_are_not_silently_retyped_in_flake():
    native = success(sme.extract(sme.ExtractRequest(SourcePayload(encoded(fixture())), context("fns.sme", SME_DAY))))
    strings = success(sme.extract(sme.ExtractRequest(SourcePayload(encoded(fixture(as_strings=True))), context("fns.sme", SME_DAY))))
    left = next(field for record in native.records if record.values()["cnt_level"] == 0 for field in record.fields if field.name == "cnt_total")
    right = next(field for record in strings.records if record.values()["cnt_level"] == 0 for field in record.fields if field.name == "cnt_total")
    assert (left.kind, left.raw_token, right.kind, right.raw_token) == ("integer", "101", "string", '"101"')
    compared = success(sme.compare_flakes(sme.CompareFlakesRequest(native, strings)))
    assert compared.state == "revised"
    before = success(sme.align(sme.ProjectionRequest(success(sme.project(sme.FlakeRequest(native))))))
    after = success(sme.align(sme.ProjectionRequest(success(sme.project(sme.FlakeRequest(strings))))))
    assert [item.value for item in before.batch.observations] == [item.value for item in after.batch.observations]
    assert before.identity != after.identity
    comparison = success(sme.compare_datasets(sme.CompareDatasetsRequest(before, after)))
    assert comparison.comparable == len(before.batch.observations)
    assert all(item.kind == "unchanged" and item.delta == 0 for item in comparison.changes)


def test_source_admission_does_not_pretend_to_validate_dates_or_counter_semantics():
    wrong_date = success(sme.extract(sme.ExtractRequest(SourcePayload(encoded(fixture(date(2026, 11, 9)))), context("fns.sme", SME_DAY))))
    report = success(sme.validate(sme.FlakeRequest(wrong_date)))
    assert not report.valid
    assert {finding.code for finding in report.findings} >= {"source.source_date_mismatch"}
    assert sme.project(sme.FlakeRequest(wrong_date)).outcome == "failed"
    # Duplicate nested fields are rejected even before the domain projection.
    raw = encoded(fixture()).replace(b'"cnt_level": 2', b'"future": {"x": 1, "x": 2}, "cnt_level": 2', 1)
    result = sme.extract(sme.ExtractRequest(SourcePayload(raw), context("fns.sme", SME_DAY)))
    assert result.outcome == "failed" and result.diagnostics[0].code == "source.json_duplicate_key"


def test_every_semantic_boundary_roundtrips_without_original_or_excel_engine(monkeypatch):
    processed = success(sme.process(sme.ProcessRequest(SourcePayload(encoded(sme_source())), context("fns.sme", SME_DAY))))
    for name, value, request in (
        ("projection", processed.projection, sme.ProjectionRequest),
        ("dataset", processed.dataset, sme.DatasetRequest),
        ("view", processed.view, sme.ViewValueRequest),
    ):
        snapshot = success(getattr(sme, name + "_snapshot")(request(value)))
        replay = success(getattr(sme, "read_" + name + "_snapshot")(sme.SnapshotRequest(retained(snapshot))))
        assert replay == value and replay.identity == value.identity
    def unavailable(*args, **kwargs):
        raise AssertionError("A retained view must not open an original workbook")
    import stratbox.core.formats.spreadsheets.extracts as physical
    monkeypatch.setattr(physical, "extract_workbook", unavailable)
    replay = success(sme.read_view_snapshot(sme.SnapshotRequest(retained(success(sme.view_snapshot(sme.ViewValueRequest(processed.view)))))))
    assert success(sme.render(sme.RenderRequest(replay))).data == processed.representation.data
    xlsx = success(sme.render(sme.RenderRequest(replay, "xlsx")))
    import openpyxl
    with BytesIO(xlsx.data) as stream:
        book = openpyxl.load_workbook(stream, data_only=False)
        assert book.sheetnames == ["Observations", "Context"]
        assert book["Observations"].freeze_panes == "A2"
        assert all(cell.data_type != "f" for sheet in book for row in sheet for cell in row)


@pytest.mark.parametrize("day,epoch,indicators,kinds", FORM_EPOCHS, ids=[item[1] for item in FORM_EPOCHS])
def test_1yur_dated_mapping_uses_retained_cells_with_original_geography(day, epoch, indicators, kinds, monkeypatch):
    source = SourcePayload(form_workbook(indicators, kinds, legacy=epoch == "A"))
    flake = success(legal_entities.extract(legal_entities.ExtractRequest(source, context("fns.1yur", day))))
    assert flake.members and flake.members[0][1].format == ("xls" if epoch == "A" else "xlsx")
    import stratbox.domains.fns.tables.legal_entities.history as history
    monkeypatch.setattr(history, "open_source_workbook", lambda *a, **k: pytest.fail("projection reopened original bytes"))
    projection = success(legal_entities.project(legal_entities.FlakeRequest(flake)))
    assert all(item.evidence_ref.startswith("member:main:sheet:") and ":cell:" in item.evidence_ref for item in projection.batch.observations)
    dataset = success(legal_entities.align(legal_entities.ProjectionRequest(projection)))
    assert json.loads(dataset.details_json)["epoch"] == epoch
    assert dataset.coverage.status == "partial"
    assert {item.perimeter for item in dataset.batch.observations} == {"published_national", "published_district", "published_territory"}
    ceased = [item for item in dataset.batch.observations if item.metric.id == "ceased_bankruptcy_liquidation"]
    assert ceased and all(item.metric.quantity_kind == "count" for item in ceased)
    assert "source.ceased_bankruptcy_period_basis_unresolved" in dataset.qualifications
    if epoch == "B":
        assert any(item.metric.id == "c01_1023" for item in projection.batch.observations)
        assert not any(dict(item.dimensions).get("source_legal_kind") == "1023" for item in dataset.batch.observations)
        assert any(item.source_field == "c01_1023" and item.target_field is None for item in dataset.dispositions)
        assert "source.unmapped_historical_fields" in dataset.qualifications
    if epoch == "A":
        assert any("formula expressions are unavailable" in item for item in flake.qualifications)


def test_1yur_all_workbooks_unselected_cells_and_member_omissions_survive_replay():
    day, _, indicators, kinds = FORM_EPOCHS[-1]
    raw = form_workbook(indicators, kinds)
    import openpyxl
    book = openpyxl.load_workbook(BytesIO(raw))
    notes = book.create_sheet("Unselected evidence")
    notes["B12"] = "This source note is retained before the business projection"
    notes["C12"] = "=1+1"
    with BytesIO() as stream:
        book.save(stream)
        raw = stream.getvalue()
    original = SourcePayload(zip_bytes({"release_I.xlsx": raw, "release_II.xlsx": raw,
        "broken.xls": b"not a workbook", "publisher-note.txt": b"Source note"}))
    flake = success(legal_entities.extract(legal_entities.ExtractRequest(original, context("fns.1yur", day))))
    assert len(flake.members) == 2 and len(flake.inventory) == 4
    assert flake.coverage.status == "partial"
    assert {item.disposition for item in flake.inventory} == {"extracted", "rejected_workbook", "original_only"}
    snapshot = success(legal_entities.flake_snapshot(legal_entities.FlakeRequest(flake)))
    replay = success(legal_entities.read_flake_snapshot(legal_entities.SnapshotRequest(retained(snapshot))))
    assert replay == flake
    note = next(sheet for sheet in replay.members[0][1].sheets if sheet.name == "Unselected evidence")
    assert note.cell(12, 2).value.startswith("This source note")
    assert note.cell(12, 3).formula == "1+1"
    projection = success(legal_entities.project(legal_entities.FlakeRequest(replay)))
    assert any(item.source_field == "member:release_II.xlsx" and item.target_field is None for item in projection.dispositions)
    assert original.identity == projection.batch.lineage[0].identity
    assert all(item.container == original.identity for item in projection.batch.lineage[1:])
    missing = next(item for item in replay.coverage.dimensions if item.name == "workbook_members")
    assert missing.missing == ("broken.xls",)


def test_1yur_part_ii_is_extractable_but_has_no_fake_part_i_projection():
    day, _, indicators, kinds = FORM_EPOCHS[-1]
    flake = success(legal_entities.extract(legal_entities.ExtractRequest(
        SourcePayload(zip_bytes({"release_II.xlsx": form_workbook(indicators, kinds)})), context("fns.1yur", day))))
    assert len(flake.members) == 1
    result = legal_entities.project(legal_entities.FlakeRequest(flake))
    assert result.outcome == "failed" and result.diagnostics[0].code == "source.source_only_part_ii_present"


def test_reviewed_june_2019_sparse_categories_remain_in_flake_and_qualify_projection():
    import openpyxl
    from stratbox.domains.fns.integration.legal_entities.mapping import KINDS
    kinds = tuple(KINDS)[:33]
    book = openpyxl.load_workbook(BytesIO(form_workbook((1, 12), " ".join(kinds))))
    for kind in kinds:
        sheet = book[kind]
        row = next(row for row in range(1, sheet.max_row + 1) if sheet.cell(row, 1).value == "53")
        sheet.cell(row, 2, "Новгородская область")
        if kind != "1000":
            sheet.delete_rows(row)
    with BytesIO() as stream:
        book.save(stream)
        payload = SourcePayload(stream.getvalue())
    release = context("fns.1yur", date(2019, 6, 1))
    flake = success(legal_entities.extract(legal_entities.ExtractRequest(payload, release)))
    assert len(set(kinds) & {sheet.name for sheet in flake.members[0][1].sheets}) == 33
    projection = success(legal_entities.project(legal_entities.FlakeRequest(flake)))
    assert {dict(item.dimensions)["source_legal_kind"] for item in projection.batch.observations} == {"1000"}
    missing = next(dimension for dimension in projection.coverage.dimensions if dimension.name == "legal_kinds")
    assert len(missing.missing) == 32
    dataset = success(legal_entities.align(legal_entities.ProjectionRequest(projection)))
    assert "source.incomplete_legal_kind_projection" in dataset.qualifications
    snapshot = success(legal_entities.dataset_snapshot(legal_entities.DatasetRequest(dataset)))
    assert success(legal_entities.read_dataset_snapshot(legal_entities.SnapshotRequest(retained(snapshot)))) == dataset
    unreviewed = replace(flake, context=context("fns.1yur", date(2019, 7, 1)))
    assert legal_entities.project(legal_entities.FlakeRequest(unreviewed)).outcome == "failed"


def test_stock_changes_and_shares_have_explicit_semantics_and_both_inputs():
    before = sme_dataset()
    after = sme_dataset(date(2026, 12, 10), increment=4)
    calculation = success(sme.calculate_changes(sme.ChangesRequest(before, after, ("total",))))
    subject = next(item for item in calculation.batch.observations if item.subject.namespace == "fns.ssrf" and item.subject.id == "01")
    assert subject.value == 4 and subject.value_status == "derived"
    assert subject.metric.id == "total.net_change" and subject.metric.quantity_kind == "count"
    assert subject.period.start == SME_DAY and subject.period.end == date(2026, 12, 10)
    assert "before:" in subject.evidence_ref and "|after:" in subject.evidence_ref
    assert "calculation.net_stock_change_is_not_entries_or_exits" in calculation.qualifications
    snapshot = success(sme.calculation_snapshot(sme.CalculationRequest(calculation)))
    assert success(sme.read_calculation_snapshot(sme.SnapshotRequest(retained(snapshot)))) == calculation
    ratios = success(sme.calculate_shares(sme.SharesRequest(before, "ul_micro", "ul_total",
        (("geographic_level", "0"),), (("geographic_level", "0"),))))
    ratio = ratios.batch.observations[0]
    assert ratio.metric.unit == "ratio" and ratio.metric.quantity_kind == "ratio"
    assert abs(ratio.value - Decimal(40) / Decimal(51)) < Decimal("1e-27")
    assert ratio.value_status == "derived" and "denominator:" in ratio.evidence_ref
    view = success(sme.view(sme.ViewRequest(calculation)))
    assert success(sme.render(sme.RenderRequest(view, "json"))).media_type == "application/json"


def test_calculations_reject_unresolved_count_periods_ambiguous_rows_and_coverage_gaps():
    before = sme_dataset()
    after = sme_dataset(date(2026, 12, 10))
    ambiguous = replace(after, batch=replace(after.batch, observations=(*after.batch.observations, after.batch.observations[0])))
    assert sme.calculate_changes(sme.ChangesRequest(before, ambiguous, ("total",))).outcome == "failed"
    gap = replace(after, batch=replace(after.batch, observations=after.batch.observations[1:]))
    assert sme.calculate_changes(sme.ChangesRequest(before, gap, ("total",))).diagnostics[0].code == "fns.calculation.coverage_mismatch"
    changed = tuple(replace(item, metric=replace(item.metric, quantity_kind="count")) for item in after.batch.observations)
    unresolved = replace(after, batch=replace(after.batch, observations=changed))
    assert sme.calculate_changes(sme.ChangesRequest(before, unresolved, ("total",))).outcome == "failed"


def test_cross_family_snapshot_replay_and_resource_overruns_are_rejected():
    dataset = sme_dataset()
    snapshot = success(sme.dataset_snapshot(sme.DatasetRequest(dataset)))
    result = legal_entities.read_dataset_snapshot(legal_entities.SnapshotRequest(snapshot))
    assert result.outcome == "failed" and result.diagnostics[0].code == "fns.source_family_mismatch"
    result = sme.read_dataset_snapshot(sme.SnapshotRequest(snapshot),
        context=ExecutionContext(budget=ExecutionBudget(cells=1)))
    assert result.outcome == "failed" and result.diagnostics[0].code == "budget.cells"


def test_rendered_and_readable_artifacts_bind_to_neutral_material_storage():
    from stratbox.shared.materials import restore_artifact
    processed = success(sme.process(sme.ProcessRequest(SourcePayload(encoded(sme_source())), context("fns.sme", SME_DAY))))
    for artifact in (
        success(sme.render_artifact(sme.RenderRequest(processed.view))),
        success(sme.readable_artifact(sme.FlakeRequest(processed.flake))),
    ):
        assert artifact.source_asset.series_id == "fns.sme"
        assert artifact.source_asset.issue_id == SME_DAY.isoformat()
        assert restore_artifact(artifact.descriptor, artifact.representation.data) == artifact
        assert artifact.inputs


def test_snapshot_version_includes_context_and_interpretation_not_just_original_bytes():
    dataset = sme_dataset()
    first = success(sme.dataset_snapshot(sme.DatasetRequest(dataset)))
    changed = replace(dataset, details_json='{"mapping_annotation":"second interpretation"}')
    second = success(sme.dataset_snapshot(sme.DatasetRequest(changed)))
    assert first.manifest.version_id != second.manifest.version_id
    assert first.manifest.dataset_id == second.manifest.dataset_id
    flake = success(sme.extract(sme.ExtractRequest(SourcePayload(encoded(sme_source())), context("fns.sme", SME_DAY))))
    recaptured = replace(flake, context=replace(flake.context, captured_at=datetime(2026, 11, 22, tzinfo=timezone.utc)))
    original = success(sme.flake_snapshot(sme.FlakeRequest(flake)))
    later = success(sme.flake_snapshot(sme.FlakeRequest(recaptured)))
    assert original.manifest.version_id != later.manifest.version_id


def test_capture_records_capture_time_separately_from_publication_and_observation_dates():
    from stratbox.core.network import HttpResponse
    observed = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    class Transport:
        def exchange(self, request, *, cancelled=None):
            return HttpResponse(200, encoded(sme_source()), {"Content-Type": "application/json"},
                observed, "https://rmsp.nalog.ru")
    result = sme.capture_full(sme.CaptureFullRequest(context("fns.sme", SME_DAY)), transport=Transport())
    value = success(result)
    assert value.flake.context.captured_at == observed
    assert value.flake.context.observation_date == value.flake.context.published_on == SME_DAY
    assert value.acquisition.observed_at_utc == observed
    assert value.original.data == encoded(sme_source())
    assert value.original.identity == value.acquisition.identity
    assert result.computation is not None


def test_full_layers_and_artifacts_can_be_stored_and_read_through_neutral_adapters(tmp_path):
    from stratbox.core.storage.filestore import LocalFileStore
    from stratbox.core.storage.datasets import FileDatasetStore
    from stratbox.core.storage.datasets.definitions import WriteSnapshotRequest, ReadSnapshotRequest
    from stratbox.core.storage.datasets.operations import write_snapshot, read_snapshot
    from stratbox.core.operations.materials.definitions import ArtifactDestination, SaveArtifactRequest, ReadArtifactRequest
    from stratbox.core.operations.materials.operations import save_artifact, read_artifact
    processed = success(sme.process(sme.ProcessRequest(SourcePayload(encoded(sme_source())), context("fns.sme", SME_DAY))))
    store = LocalFileStore(root=str(tmp_path))
    datasets = FileDatasetStore(store, "datasets", provider_id="test.local", scope_id="fns")
    for layer, value, request in (("flake", processed.flake, sme.FlakeRequest),
        ("projection", processed.projection, sme.ProjectionRequest),
        ("dataset", processed.dataset, sme.DatasetRequest), ("view", processed.view, sme.ViewValueRequest)):
        encoded_layer = getattr(sme, layer + "_snapshot")(request(value))
        snapshot = success(encoded_layer)
        assert encoded_layer.computation is not None
        reference = success(write_snapshot(WriteSnapshotRequest(snapshot), store=datasets)).reference
        stored = success(read_snapshot(ReadSnapshotRequest(reference), store=datasets))
        assert success(getattr(sme, "read_" + layer + "_snapshot")(sme.SnapshotRequest(stored))) == value
    artifact = success(sme.render_artifact(sme.RenderRequest(processed.view)))
    saved = success(save_artifact(SaveArtifactRequest(artifact, ArtifactDestination("exports/fns.csv")), store=store))
    assert success(read_artifact(ReadArtifactRequest(saved.artifact), store=store)) == artifact


def test_snapshot_metadata_binds_only_the_correct_family_layer_and_actual_value_type():
    from stratbox.core.execution.handoff import HandoffError, bind_request, project_output
    from stratbox.core.storage.datasets.definitions import WRITE
    full = sme.process(sme.ProcessRequest(SourcePayload(encoded(sme_source())), context("fns.sme", SME_DAY)))
    processed = success(full)
    calculated = sme.calculate_shares(sme.SharesRequest(processed.dataset, "ul_micro", "ul_total",
        (("geographic_level", "0"),), (("geographic_level", "0"),)))
    calculation = success(calculated)
    values = (
        ("flake", processed.flake, sme.FlakeRequest),
        ("projection", processed.projection, sme.ProjectionRequest),
        ("dataset", processed.dataset, sme.DatasetRequest),
        ("calculation", calculation, sme.CalculationRequest),
        ("view", processed.view, sme.ViewValueRequest),
    )
    for layer, value, request in values:
        encoded_layer = getattr(sme, layer + "_snapshot")(request(value))
        snapshot = success(encoded_layer)
        assert type(snapshot) is DatasetSnapshot
        precise = project_output(encoded_layer, "snapshot")
        generic = project_output(encoded_layer, "dataset_snapshot")
        assert precise.contract == snapshot.manifest.contract
        definition = getattr(sme, "READ_" + layer.upper() + "_SNAPSHOT")
        bound = bind_request(definition, {"snapshot": precise})
        assert type(bound.request.snapshot) is DatasetSnapshot
        assert success(bound.invoke(getattr(sme, "read_" + layer + "_snapshot"))) == value
        assert bind_request(WRITE, {"snapshot": generic}).request.snapshot is snapshot
        with pytest.raises(HandoffError, match="schema_mismatch"):
            bind_request(definition, {"snapshot": generic})
        with pytest.raises(HandoffError, match="schema_mismatch"):
            bind_request(getattr(legal_entities, "READ_" + layer.upper() + "_SNAPSHOT"), {"snapshot": precise})
        for other_layer, _, _ in values:
            if other_layer != layer:
                with pytest.raises(HandoffError, match="schema_mismatch"):
                    bind_request(getattr(sme, "READ_" + other_layer.upper() + "_SNAPSHOT"), {"snapshot": precise})
        live = project_output(calculated if layer == "calculation" else full, layer)
        with pytest.raises(HandoffError, match="schema_mismatch"):
            bind_request(definition, {"snapshot": live})
