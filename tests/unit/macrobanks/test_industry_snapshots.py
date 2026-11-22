"""A retained source flake can finish the analytical route without its workbook."""
from dataclasses import replace
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.corporate_lending.industries import debt_0105a as debt, issuance_0104 as issuance
from stratbox.domains.cbr.corporate_lending.industries.common.contracts import IndustryPivotRequest
from stratbox.domains.cbr.corporate_lending.industries.debt_0105a.derived import CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES

from test_cbr_industries_0104a_issuance import _book as issuance_workbook, _request as issuance_request
from test_cbr_industries_0105a_debt_corp import _workbook_bytes


def _ok(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def _parsed(family):
    selection = debt.IndustrySelection(tuple(CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES))
    if family == "debt":
        request = debt.ParseIndustryRequest(SourcePayload(_workbook_bytes(
            report_date="01.02.2019", kemerovo_name="Кемеровская область")),
            "01_05_A_Debt_corp_20190201.xlsx", selection=selection)
        return debt, _ok(debt.parse(request))
    request = replace(issuance_request(), selection=selection)
    return issuance, _ok(issuance.parse(request))


def _replay(domain, value, kind, path):
    snapshot = _ok(getattr(domain, f"build_{kind}_snapshot")(
        domain.IndustrySnapshotRequest(value, f"test.{kind}", "2019-02")))
    expected_identity = snapshot.identity
    stored = _ok(write_snapshot(WriteSnapshotRequest(snapshot), store=FileDatasetStore(
        LocalFileStore(path), "datasets", provider_id="files", scope_id="test")))
    # Reopen with an independent adapter. Neither the live value nor its source
    # workbook is supplied to the reader or any subsequent operation.
    recovered = _ok(read_snapshot(ReadSnapshotRequest(stored.reference), store=FileDatasetStore(
        LocalFileStore(path), "datasets", provider_id="files", scope_id="test")))
    assert recovered.identity == expected_identity
    result = _ok(getattr(domain, f"read_{kind}_snapshot")(domain.ReadIndustrySnapshotRequest(recovered)))
    assert result.evidence == value.evidence
    return result


@pytest.mark.parametrize("family", ["debt", "issuance"])
def test_all_stages_replay_before_final_render(family, tmp_path):
    domain, parsed = _parsed(family)
    restored = _replay(domain, parsed, "flake", tmp_path)
    pd.testing.assert_frame_equal(restored.df_stream, parsed.df_stream)
    assert restored.source_sha256 == parsed.source_sha256
    assert restored.geography_reference_version == parsed.geography_reference_version
    assert restored.selection == parsed.selection
    request = (debt.IntegrateIndustryFlakesRequest((restored,)) if family == "debt"
               else issuance.IntegrateIssuanceFlakesRequest((restored,)))
    integrated = _ok(domain.integrate_flakes(request))
    integrated = _replay(domain, integrated, "stream", tmp_path)
    calculate = (debt.CalculateApkRequest(integrated) if family == "debt"
                 else issuance.CalculateIssuanceApkRequest(integrated))
    derived = _replay(domain, _ok(domain.calculate_apk(calculate)), "calculation", tmp_path)
    pivot = IndustryPivotRequest("region_code", "report_date", sheet_dimensions=("measure", "currency_scope"))
    request = (debt.PivotInput(derived, pivot, industry_code="apk") if family == "debt"
               else issuance.PivotIssuanceRequest(derived, pivot, industry_code="apk"))
    prepared = _replay(domain, _ok(domain.build_pivots(request)), "view", tmp_path)
    if family == "debt":
        rendered = _ok(debt.render_pivots(debt.RenderPivotRequest(prepared)))
        expected_sheets = 6
    else:
        assert integrated.dates == ("2019-02-01",)
        assert integrated.reference_periods == ("2019-01",)
        rendered = _ok(issuance.render_pivots(issuance.RenderIssuancePivotsRequest(
            prepared, "apk", derived.industry.canonical_name_ru, integrated.reference_periods)))
        expected_sheets = 3
    workbook = load_workbook(BytesIO(rendered.representation.data), read_only=True, data_only=True)
    assert len(workbook.sheetnames) == expected_sheets
    workbook.close()


def test_partial_snapshot_and_wrong_family_are_rejected(tmp_path):
    domain, value = _parsed("issuance")
    snapshot = _ok(domain.build_flake_snapshot(domain.IndustrySnapshotRequest(value, "test.flake", "2019-02")))
    partial = DatasetSnapshot(snapshot.manifest, snapshot.tables[:1])
    assert domain.read_flake_snapshot(domain.ReadIndustrySnapshotRequest(partial)).outcome == "failed"
    assert debt.read_flake_snapshot(debt.ReadIndustrySnapshotRequest(snapshot)).outcome == "failed"
    changed = replace(value, reference_period="2018-12")
    assert domain.build_flake_snapshot(domain.IndustrySnapshotRequest(changed, "test.flake", "wrong")).outcome == "failed"


def test_integration_has_explicit_release_coverage_and_conflict_policy():
    domain, value = _parsed("issuance")
    duplicate = domain.integrate_flakes(domain.IntegrateIssuanceFlakesRequest((value, value)))
    assert duplicate.outcome == "failed"
    assert duplicate.diagnostics[0].code == "request.duplicate_release"
    partial = domain.integrate_flakes(domain.IntegrateIssuanceFlakesRequest(
        (value,), expected_report_dates=("2019-02-01", "2019-03-01")))
    assert partial.outcome == "partial"
    assert partial.value.is_partial
    assert partial.value.latest_report_date == "2019-02-01"
    assert partial.value.latest_discovered_report_date == "2019-03-01"
    assert domain.calculate_apk(domain.CalculateIssuanceApkRequest(partial.value)).outcome == "failed"


def test_discovery_declares_optional_http_and_preserves_offline_route():
    assert issuance.DISCOVER.optional_capabilities == frozenset({"http"})
    payload = SourcePayload(b'<a href="/vfs/statistics/01_04_A_New_loans_corp_20190201.xlsx">issue</a>')
    result = issuance.discover(issuance.DiscoverIssuanceRequest(index=payload))
    assert result.outcome == "succeeded", result.diagnostics


@pytest.mark.parametrize("family", ["debt", "issuance"])
def test_composed_history_exports_independent_original_flakes(family, tmp_path):
    selection = debt.IndustrySelection(("total",))
    if family == "debt":
        domain = debt
        sources = tuple(debt.ParseIndustryRequest(SourcePayload(_workbook_bytes(
            report_date=printed, kemerovo_name=region)),
            f"01_05_A_Debt_corp_{day}.xlsx", selection=selection)
            for day, printed, region in (
                ("20190201", "01.02.2019", "Кемеровская область"),
                ("20260601", "01.06.2026", "Кемеровская область - Кузбасс")))
        request = debt.BuildIndustryStreamRequest(sources, selection=selection)
        integration = debt.IntegrateIndustryFlakesRequest
    else:
        domain = issuance
        sources = tuple(issuance.ParseIssuanceRequest(SourcePayload(issuance_workbook(date_text=month)),
            f"01_04_A_New_loans_corp_{day}.xlsx", selection=selection)
            for day, month in (("20190201", "Январь 2019"), ("20260601", "Май 2026")))
        request = issuance.BuildIssuanceStreamRequest(sources, selection=selection)
        integration = issuance.IntegrateIssuanceFlakesRequest
    composed = _ok(domain.build_stream(request))
    retained = []
    for source_request, flake in zip(sources, composed.parsed_files, strict=True):
        independent = _ok(domain.parse(source_request))
        # A nested flake has precisely the standalone extraction identity and
        # original geography, even when the aggregate uses a later reference.
        assert flake.evidence == independent.evidence
        assert len(flake.evidence.inputs) == 1
        assert flake.evidence.inputs[0].identity == source_request.payload.identity
        pd.testing.assert_frame_equal(flake.df_stream, independent.df_stream)
        retained.append(_replay(domain, flake, "flake", tmp_path / flake.report_date))
    reintegrated = _ok(domain.integrate_flakes(integration(tuple(retained))))
    pd.testing.assert_frame_equal(reintegrated.df_stream, composed.df_stream)
    assert reintegrated.dates == composed.dates
    assert reintegrated.regions == composed.regions
    assert reintegrated.evidence.parents == composed.evidence.parents
    assert reintegrated.evidence.inputs == tuple(
        item for item in composed.evidence.inputs if item.role.startswith("flake_"))
