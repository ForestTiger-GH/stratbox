"""Source observations remain reusable before any SORS model is selected."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import openpyxl
import pandas as pd
import pytest

from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.tables.corporate_lending.observations import extract_observations
from stratbox.domains.cbr.operations.corporate_lending.source_definitions import (
    CorporateObservationSnapshotRequest, ExtractCorporateObservationsRequest,
    ReadCorporateObservationSnapshotRequest,
)
from stratbox.domains.cbr.operations.corporate_lending.source_operations import extract, build_snapshot, read_snapshot
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.common import source_records
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.source_publications import SourceAssetIdentity


EXACT = "12345678901234567890.1234500"


def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def workbook_flake(*, missing=True, flow=False, asset_id="main"):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Published"
    sheet.append(["Объем кредитов в рублях, млн руб." if flow else "Задолженность в рублях, млн руб."])
    sheet.append(["Класс ОКВЭД2", "Май 2026" if flow else datetime(2026, 5, 1),
                  "Июнь 2026" if flow else datetime(2026, 6, 1)])
    sheet.append(["01-Растениеводство", 987654321, 17])
    sheet.append(["02-Лесоводство", None if missing else 4, "—" if missing else 5])
    sheet.append(["03-Рыболовство", "12,40", "=C3+1" if missing else 18])
    body = BytesIO()
    book.save(body)
    exact = BytesIO()
    with ZipFile(BytesIO(body.getvalue())) as source, ZipFile(exact, "w", ZIP_DEFLATED) as target:
        for name in source.namelist():
            data = source.read(name)
            if name == "xl/worksheets/sheet1.xml":
                data = data.replace(b"<v>987654321</v>", ("<v>" + EXACT + "</v>").encode())
            target.writestr(name, data)
    series = "cbr.corporate_lending.corp_new_loans_c" if flow else "cbr.corporate_lending.corp_debt_c"
    return extract_workbook_value(IdentifiedOriginal(
        SourceAssetIdentity(series, "capture.2026-06-20", asset_id), SourcePayload(exact.getvalue()), "xlsx"))


def test_all_source_periods_precision_missing_cells_and_replay():
    flake = workbook_flake()
    value = checked(extract(ExtractCorporateObservationsRequest(flake)))
    assert value.available_periods == ("2026-05-01", "2026-06-01")
    assert value.selected_periods == value.available_periods
    assert len(value.observations) == 6
    cells = value.observations.set_index("coordinate")
    assert cells.loc["B3", "value"] == Decimal(EXACT)
    assert cells.loc["B3", "raw_token"] == EXACT
    assert cells.loc["B3", "period_basis"] == "as_of"
    assert cells.loc["B4", "status"] == "blank"
    assert cells.loc["C4", "status"] == "marker"
    assert cells.loc["B5", "value"] == Decimal("12.40")
    assert cells.loc["C5", "status"] == "formula_unresolved"
    assert cells.loc["C5", "formula"] == "C3+1"
    assert value.source_identity == flake.source_identity
    assert value.asset_id == "main"
    assert not {"published_lower", "published_upper", "geography_node_id"} & set(cells.columns)
    encoded = checked(build_snapshot(CorporateObservationSnapshotRequest(value)))
    restored = checked(read_snapshot(ReadCorporateObservationSnapshotRequest(encoded)))
    pd.testing.assert_frame_equal(restored.observations, value.observations)
    assert restored.evidence == value.evidence
    assert checked(build_snapshot(CorporateObservationSnapshotRequest(restored))).identity == encoded.identity


def test_source_asset_identity_survives_projection_and_snapshot_and_limits_model_scope():
    flake = workbook_flake(missing=False, asset_id="supplement")
    value = checked(extract(ExtractCorporateObservationsRequest(flake)))
    assert value.asset_id == "supplement"
    encoded = checked(build_snapshot(CorporateObservationSnapshotRequest(value)))
    restored = checked(read_snapshot(ReadCorporateObservationSnapshotRequest(encoded)))
    assert restored.asset_id == "supplement"
    assert restored.evidence == value.evidence
    assert checked(build_snapshot(CorporateObservationSnapshotRequest(restored))).identity == encoded.identity
    for source in (flake, restored):
        with pytest.raises(ValueError, match="source_asset_unsupported"):
            source_records(source, "2026-05-01", "01_02_C")
    relabelled = build_snapshot(CorporateObservationSnapshotRequest(replace(restored, asset_id="main")))
    assert relabelled.outcome == "failed"
    assert relabelled.diagnostics[0].code == "cbr.corporate.observation_identity_mismatch"


def test_selection_is_explicit_and_flow_periods_are_reference_months():
    flake = workbook_flake(flow=True)
    value = checked(extract(ExtractCorporateObservationsRequest(flake, ("2026-06",))))
    assert value.available_periods == ("2026-05", "2026-06")
    assert value.selected_periods == ("2026-06",)
    assert value.coverage.status == "partial"
    assert set(value.observations["quantity_kind"]) == {"flow"}
    assert set(value.observations["period_basis"]) == {"reference_month"}
    assert set(value.observations["period_raw"]) == {"Июнь 2026"}
    with pytest.raises(ValueError, match="period_missing"):
        extract_observations(flake, periods=("2025-06",))


def test_district_flake_keeps_flow_and_stock_sheets_with_distinct_period_bases():
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, title in (("Flow", "Объем кредитов в рублях, за май 2026, млн руб."),
                        ("Stock", "Задолженность в рублях на 01.06.2026, млн руб.")):
        sheet = book.create_sheet(name)
        sheet.append([title])
        sheet.append(["Округ", *(letter + ". Published section" for letter in "ABCDEFGHIJKLMNOP")])
        sheet.append(["ЦЕНТРАЛЬНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ", *range(16)])
    data = BytesIO()
    book.save(data)
    original = IdentifiedOriginal(SourceAssetIdentity("cbr.corporate_lending.fd_okved2", "2026-06-01", "main"),
                                  SourcePayload(data.getvalue()), "xlsx")
    observations = checked(extract(ExtractCorporateObservationsRequest(extract_workbook_value(original))))
    assert observations.diagnostics == ()
    assert len(observations.observations) == 32
    assert observations.available_periods == ("2026-05", "2026-06-01")
    source = observations.observations
    assert set(source.loc[source["measure"].eq("issuance"), "period_basis"]) == {"reference_month"}
    assert set(source.loc[source["measure"].eq("debt"), "period_basis"]) == {"as_of"}
    assert len(source_records(observations, "2026-06-01", "01_03_C")) == 16


def test_model_admission_selects_a_period_without_changing_the_source_value():
    value = checked(extract(ExtractCorporateObservationsRequest(workbook_flake(missing=False))))
    model = source_records(value, "2026-05-01", "01_02_C")
    assert len(model) == 3
    assert model.iloc[0]["source_value"] == Decimal(EXACT)
    assert model.iloc[0]["raw_token"] == EXACT
    assert pd.api.types.is_float_dtype(model["value"].dtype)
    with pytest.raises(ValueError, match="missing_or_unresolved"):
        source_records(workbook_flake(), "2026-06-01", "01_02_C")


def test_tampering_and_raw_inputs_do_not_cross_prepared_boundaries(monkeypatch):
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceInputs
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import DEPENDENCIES
    from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsRunConfig
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import PrepareSorsRequest, RestoreSorsRequest
    from stratbox.domains.cbr.operations.corporate_lending.sors.api import prepare_inputs, restore
    import stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.loader as loader

    value = checked(extract(ExtractCorporateObservationsRequest(workbook_flake())))
    value.observations.loc[0, "value"] = Decimal("0")
    encoded = build_snapshot(CorporateObservationSnapshotRequest(value))
    assert encoded.outcome == "failed"
    assert encoded.diagnostics[0].code == "cbr.corporate.observation_identity_mismatch"
    sources = SorsSourceInputs(**{item.input_name: SourcePayload(b"fixture")
                                 for item in DEPENDENCIES if item.required})
    def forbidden(*args, **kwargs):
        raise AssertionError("Source extraction is outside the prepared-input operation")
    monkeypatch.setattr(loader, "parse_source_inputs", forbidden)
    prepared = prepare_inputs(PrepareSorsRequest(sources, SorsRunConfig("2026-06-01")))
    assert prepared.diagnostics[0].code == "sors.source_observations_required"
    restored = restore(RestoreSorsRequest(sources, SorsRunConfig("2026-06-01")))
    assert restored.diagnostics[0].code == "sors.prepared_bundle_required"
