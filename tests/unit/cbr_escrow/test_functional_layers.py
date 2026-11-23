"""Semantic boundaries between source extraction, integration and presentation."""
from dataclasses import replace
from datetime import date
from io import BytesIO

from openpyxl import load_workbook

from stratbox.domains.cbr.operations import project_finance as escrow
from stratbox.domains.cbr.integration.project_finance.snapshots import dataset_snapshot
from stratbox.domains.cbr.products.project_finance.profiles import DEFAULT_PRODUCT_PROFILE
from stratbox.domains.cbr.tables.project_finance.snapshots import flake_snapshot
from stratbox.shared.evidence import SourcePayload

from .test_replay import checked, publication


def test_product_style_changes_neither_extracted_nor_integrated_identity():
    request = publication()
    flake = checked(escrow.parse(request))
    dataset = checked(escrow.integrate_flakes(escrow.IntegrateEscrowRequest((flake,))))
    original_flake = flake_snapshot(flake).identity
    original_dataset = dataset_snapshot(dataset).identity
    before = checked(escrow.build_views(escrow.BuildEscrowViewsRequest(dataset)))
    selected = tuple(replace(item, sheet_code=f"Table_{index}", title=f"Published metric {index}",
                             number_format="0.0000")
                     for index, item in enumerate(DEFAULT_PRODUCT_PROFILE.indicators, 1))
    profile = replace(DEFAULT_PRODUCT_PROFILE, version=2, indicators=selected)
    after = checked(escrow.build_views(escrow.BuildEscrowViewsRequest(dataset,
        escrow.EscrowViewBuildRequest(profile=profile))))
    before_snapshot = checked(escrow.build_view_snapshot(escrow.EscrowViewSnapshotRequest(before)))
    after_snapshot = checked(escrow.build_view_snapshot(escrow.EscrowViewSnapshotRequest(after)))
    assert before_snapshot.identity != after_snapshot.identity
    assert flake_snapshot(checked(escrow.parse(request))).identity == original_flake
    assert dataset_snapshot(dataset).identity == original_dataset
    assert not hasattr(flake.resolved_columns[0].spec, "sheet_code")
    assert not hasattr(dataset.indicator_specs[0], "required_tokens")
    book = load_workbook(BytesIO(checked(escrow.render_workbook(after)).data))
    assert book.sheetnames[0] == "Table_1"
    assert book["Table_1"]["B5"].number_format == "0.0000"
    book.close()


def test_history_composition_returns_the_same_integrated_dataset_contract():
    requests = (publication(), publication(period="01072026", region="New region"))
    composed = checked(escrow.build_history(escrow.EscrowHistoryBuildRequest(requests)))
    flakes = tuple(checked(escrow.parse(request)) for request in requests)
    independent = checked(escrow.integrate_flakes(escrow.IntegrateEscrowRequest(flakes, coverage=composed.coverage)))
    assert type(composed) is type(independent) is escrow.EscrowDataset
    assert dataset_snapshot(composed).identity == dataset_snapshot(independent).identity
    result = escrow.build_views(escrow.BuildEscrowViewsRequest(flakes[0]))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "request.integrated_dataset_required"


def test_prepared_product_replays_custom_style_and_exact_original_version_vector(monkeypatch):
    requests = (publication(), publication(period="01072026"))
    dataset = checked(escrow.build_history(escrow.EscrowHistoryBuildRequest(requests)))
    profile = replace(DEFAULT_PRODUCT_PROFILE, version=2,
        indicators=tuple(replace(item, sheet_code=f"View_{i}") for i, item in enumerate(DEFAULT_PRODUCT_PROFILE.indicators, 1)))
    view = checked(escrow.build_views(escrow.BuildEscrowViewsRequest(dataset, escrow.EscrowViewBuildRequest(profile=profile))))
    snapshot = checked(escrow.build_view_snapshot(escrow.EscrowViewSnapshotRequest(view)))
    restored = checked(escrow.read_view_snapshot(escrow.ReadEscrowSnapshotRequest(snapshot)))
    assert tuple(item.identity for item in restored.input_versions) == tuple(request.payload.identity for request in requests)
    assert snapshot.manifest.inputs[1:] == restored.input_versions
    assert restored.indicator_specs == view.indicator_specs
    assert restored.product_profile_version == 2

    def unexpected(*args, **kwargs):
        raise AssertionError("Rendering a saved view must not reconstruct its earlier stages")
    monkeypatch.setattr("stratbox.domains.cbr.tables.project_finance.parser.parse_escrow_excel_bytes", unexpected)
    monkeypatch.setattr("stratbox.domains.cbr.integration.project_finance.assembly.integrate_values", unexpected)
    monkeypatch.setattr("stratbox.domains.cbr.products.project_finance.views.prepare_dataset_view", unexpected)
    assert checked(escrow.render_workbook(restored)) == checked(escrow.render_workbook(view))


def test_source_revision_comparison_distinguishes_representation_from_facts():
    before = checked(escrow.parse(publication(amount="0012.2500")))
    same_facts = checked(escrow.parse(publication(amount="12.25")))
    changed = checked(escrow.parse(publication(amount="13.25")))
    representation = checked(escrow.compare(escrow.CompareEscrowFlakesRequest(before, same_facts)))
    assert representation.bytes_changed and not representation.facts_changed
    assert not representation.issue_changed and not representation.interpretation_changed
    facts = checked(escrow.compare(escrow.CompareEscrowFlakesRequest(before, changed)))
    assert facts.facts_changed and not facts.issue_changed
    later = checked(escrow.parse(publication(period="01072026", amount="0012.2500")))
    assert checked(escrow.compare(escrow.CompareEscrowFlakesRequest(before, later))).issue_changed


def test_validation_and_readable_keep_unknown_and_unresolved_source_cells():
    flake = checked(escrow.parse(publication()))
    result = checked(escrow.validate(flake))
    assert result.unmapped_headers == ("Unmapped source measure",)
    assert result.unresolved_cells == 3
    text = checked(escrow.readable(flake)).data.decode("utf-8")
    assert "0012.2500" in text and "formula_unresolved" in text
    assert "Unmapped source measure" in text and "not understood" in text


def test_shared_observations_keep_source_geography_until_explicit_historical_mapping():
    dataset = checked(escrow.build_history(escrow.EscrowHistoryBuildRequest((publication(),))))
    result = checked(escrow.align_observations(escrow.AlignEscrowObservationsRequest(dataset)))
    unknown = next(item for item in result.observations if item.subject.id == "region:Example region")
    assert unknown.subject.namespace == "cbr.project_finance.source_geography"
    assert dict(unknown.dimensions)["geography_status"] == "source_identity"
    money = next(item for item in result.observations if item.metric.id.endswith("escrow_balance_mln_rub"))
    assert money.metric.unit == "RUB" and money.metric.scale == 1_000_000
    assert any(item.value_status == "blank" for item in result.observations)
    assert any(item.value_status == "dash" for item in result.observations)
    cumulative = next(item for item in result.observations if item.metric.id.endswith("revealed_escrow_amount_mln_rub"))
    assert cumulative.metric.quantity_kind is None
    assert dict(cumulative.dimensions)["source_period_basis"] == "cumulative_start_unspecified"
    rule = escrow.EscrowGeographyRule("Example region", "region", "reference.geography", "example",
        "example-2026", date(2026, 1, 1), date(2026, 12, 31))
    mapped = checked(escrow.align_observations(escrow.AlignEscrowObservationsRequest(dataset, (rule,))))
    assert any(item.subject.namespace == "reference.geography" and item.subject.id == "example" for item in mapped.observations)
    assert mapped.lineage[-1].identity != result.lineage[-1].identity
    ambiguous = escrow.align_observations(escrow.AlignEscrowObservationsRequest(dataset, (rule, rule)))
    assert ambiguous.outcome == "failed"
    assert ambiguous.diagnostics[0].code == "escrow.geography_mapping_ambiguous"


def test_partial_original_history_keeps_failed_sources_without_claiming_completion():
    request = publication()
    invalid = escrow.ParseEscrowRequest(SourcePayload(b"not a workbook"), "escrow_01072026.xlsx")
    result = escrow.build_history(escrow.EscrowHistoryBuildRequest((request, invalid), continue_on_error=True))
    assert result.outcome == "partial"
    assert not result.value.selection_complete
    assert result.value.failures[0][0] == invalid.source_name
    replay = checked(escrow.read_dataset_snapshot(escrow.ReadEscrowSnapshotRequest(dataset_snapshot(result.value))))
    assert replay.failures == result.value.failures
    assert escrow.build_views(escrow.BuildEscrowViewsRequest(replay)).diagnostics[0].code == "source.history_incomplete"
    assert escrow.build_views(escrow.BuildEscrowViewsRequest(replay, escrow.EscrowViewBuildRequest(require_complete_history=False))).outcome == "succeeded"
