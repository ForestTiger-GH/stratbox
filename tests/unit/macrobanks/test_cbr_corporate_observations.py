"""Source observations remain reusable before any SORS model is selected."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import openpyxl
import pandas as pd
import pytest

from stratbox.domains.cbr.methods.tables.corporate_lending.observations import extract_observations
from stratbox.domains.cbr.calculations.sors.inputs.common import source_records
from stratbox.shared.evidence import SourcePayload

from types import SimpleNamespace
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.domains.cbr.methods.actions.statistics import SourceWorkbook
from stratbox.domains.cbr.methods.actions.serialization import encode, decode
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt

_CONTEXT = SimpleNamespace(parameters={}, checkpoint=lambda: None)

def _source_workbook(data, series, issue, asset="main"):
    identity = ByteIdentity.of(data)
    return SourceWorkbook(series, issue, identity, read_workbook_cells(data).sheets, asset,
        (UsedInputReceipt("original", identity, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "inline", series),))

def _extract(flake, periods=None):
    settings = DOMAIN.series[flake.series_id].commands["command.table.interpret"].settings.corporate
    return extract_observations(flake, settings, periods=periods)

def _encode(value):
    return encode({"value": value}, None, _CONTEXT)["representation"]

def _decode(value):
    return decode({"representation": value}, None, _CONTEXT)["value"]


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
    return _source_workbook(exact.getvalue(), series, "capture.2026-06-20", asset_id)


def test_all_source_periods_precision_missing_cells_and_replay():
    flake = workbook_flake()
    value = _extract(flake)
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
    encoded = _encode(value)
    restored = _decode(encoded)
    pd.testing.assert_frame_equal(restored.observations, value.observations)
    assert restored.evidence == value.evidence
    assert _encode(restored).identity == encoded.identity


def test_source_asset_identity_survives_projection_and_snapshot_and_limits_model_scope():
    flake = workbook_flake(missing=False, asset_id="supplement")
    value = _extract(flake)
    assert value.asset_id == "supplement"
    encoded = _encode(value)
    restored = _decode(encoded)
    assert restored.asset_id == "supplement"
    assert restored.evidence == value.evidence
    assert _encode(restored).identity == encoded.identity
    for source in (flake, restored):
        with pytest.raises(ValueError, match="source_asset_unsupported"):
            source_records(source, "2026-05-01", "01_02_C")
    with pytest.raises(ValueError, match="observation_identity_mismatch"):
        _encode(replace(restored, asset_id="main"))


def test_selection_is_explicit_and_flow_periods_are_reference_months():
    flake = workbook_flake(flow=True)
    value = _extract(flake, ("2026-06",))
    assert value.available_periods == ("2026-05", "2026-06")
    assert value.selected_periods == ("2026-06",)
    assert value.coverage.status == "partial"
    assert set(value.observations["quantity_kind"]) == {"flow"}
    assert set(value.observations["period_basis"]) == {"reference_month"}
    assert set(value.observations["period_raw"]) == {"Июнь 2026"}
    with pytest.raises(ValueError, match="period_missing"):
        _extract(flake, ("2025-06",))


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
    original = _source_workbook(data.getvalue(), "cbr.corporate_lending.fd_okved2", "2026-06-01")
    observations = _extract(original)
    assert observations.diagnostics == ()
    assert len(observations.observations) == 32
    assert observations.available_periods == ("2026-05", "2026-06-01")
    source = observations.observations
    assert set(source.loc[source["measure"].eq("issuance"), "period_basis"]) == {"reference_month"}
    assert set(source.loc[source["measure"].eq("debt"), "period_basis"]) == {"as_of"}
    assert len(source_records(observations, "2026-06-01", "01_03_C")) == 16


def test_model_admission_selects_a_period_without_changing_the_source_value():
    value = _extract(workbook_flake(missing=False))
    model = source_records(value, "2026-05-01", "01_02_C")
    assert len(model) == 3
    assert model.iloc[0]["source_value"] == Decimal(EXACT)
    assert model.iloc[0]["raw_token"] == EXACT
    assert pd.api.types.is_float_dtype(model["value"].dtype)
    with pytest.raises(ValueError, match="missing_or_unresolved"):
        source_records(workbook_flake(), "2026-06-01", "01_02_C")


def test_tampering_and_raw_inputs_do_not_cross_prepared_boundaries(monkeypatch):
    from stratbox.domains.cbr.calculations.sors.inputs.common import source_dataset
    value = _extract(workbook_flake())
    value.observations.loc[0, "value"] = Decimal("0")
    with pytest.raises(ValueError, match="observation_identity_mismatch"):
        _encode(value)
    with pytest.raises(ValueError, match="observation_identity_mismatch"):
        source_records(value, "2026-05-01", "01_02_C")
    with pytest.raises(ValueError, match="interpreted_workbook_required"):
        source_dataset(SourcePayload(b"raw original"), "01_02_C")
