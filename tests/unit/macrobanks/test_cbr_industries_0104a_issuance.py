"""Offline deterministic release, parser, history, derived and workbook gates for 01_04_A."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from stratbox.data import SourcePayload
from stratbox.macrobanks.cbr_industries import issuance_0104 as issuance
from stratbox.macrobanks.cbr_industries.regions import CBR_0105A_DEBT_CORP_REGION_LAYOUT
from stratbox.macrobanks.cbr_industries.schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS
from stratbox.macrobanks.cbr_industries.issuance_0104.parser import parse_workbook
from stratbox.macrobanks.cbr_industries.issuance_0104.sources import (
    discover_links, reference_period, report_date_from_filename,
)

SHEETS = (
    ("rubles", "в рублях", 1),
    ("foreign", "в иностранной валюте и драгоценных металлах", 2),
    ("total", "", 3),
)


def _book(*, date_text="Январь 2019", wrong_industry=False,
          blank_component=False, negative=False, swapped_geography=False) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, currency_text, factor in SHEETS:
        worksheet = workbook.create_sheet(name)
        worksheet["A1"] = (
            "Объем кредитов, предоставленных юридическим лицам - резидентам "
            "и индивидуальным предпринимателям " + currency_text + ", "
            "по видам экономической деятельности и отдельным направлениям использования средств, млн руб."
        )
        worksheet["A2"] = date_text
        for col, industry in enumerate(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS, start=2):
            worksheet.cell(3, col, industry.canonical_name_ru)
        if wrong_industry:
            worksheet["C3"] = "Посторонняя отрасль"
        for row, region in enumerate(CBR_0105A_DEBT_CORP_REGION_LAYOUT, start=4):
            label = region.canonical_name
            if swapped_geography and name == "foreign" and row == 4:
                label = "Неизвестная территория"
            worksheet.cell(row, 1, label)
            for col, industry in enumerate(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS, start=2):
                base = {
                    "total": 1000,
                    "agriculture_hunting_forestry": 30,
                    "agriculture_hunting_services": 25,
                    "manufacturing_food_beverages_tobacco": 20,
                    "manufacturing_machinery_agriculture_forestry": 3,
                    "manufacturing_wood_products": 5,
                }.get(industry.code, 1)
                # Rubles + foreign currency = total: 1 + 2 = 3.
                value = base * factor
                if blank_component and name == "rubles" and row == 4 and industry.code == "manufacturing_food_beverages_tobacco":
                    value = None
                if negative and name == "rubles" and row == 4 and industry.code == "manufacturing_food_beverages_tobacco":
                    value = -1
                worksheet.cell(row, col, value)
    binary = BytesIO()
    workbook.save(binary)
    workbook.close()
    return binary.getvalue()


def _request(payload: bytes | None = None) -> issuance.ParseIssuanceRequest:
    return issuance.ParseIssuanceRequest(
        SourcePayload(payload if payload is not None else _book()),
        "01_04_A_New_loans_corp_20190201.xlsx",
    )


def _history():
    result = issuance.build_stream(issuance.BuildIssuanceStreamRequest((_request(),)))
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.ok
    return result.value


def test_release_filename_and_reference_month_cross_year() -> None:
    assert report_date_from_filename("01_04_A_New_loans_corp_20260101.xlsx") == "2026-01-01"
    assert reference_period("2026-01-01") == "2025-12"
    assert reference_period("2026-08-01") == "2026-07"
    with pytest.raises(ValueError):
        report_date_from_filename("01_04_A_New_loans_corp_20260102.xlsx")


def test_discovery_is_exact_and_date_filtered() -> None:
    html = b'''<a href="/vfs/statistics/01_04_A_New_loans_corp_20190201.xlsx">valid</a>
      <a href="/vfs/statistics/01_04_A_New_loans_corp_20190301.xlsx">valid</a>
      <a href="/vfs/statistics/01_05_A_Debt_corp_20190201.xlsx">other</a>'''
    selected = discover_links(html, date_from="2019-03-01")
    assert len(selected) == 1
    assert selected[0].report_date == "2019-03-01"
    assert selected[0].reference_period == "2019-02"
    with pytest.raises(ValueError):
        discover_links(html, date_from="2019-04-01", date_to="2019-02-01")


def test_parser_recognizes_month_geography_industries_and_cells() -> None:
    parsed = parse_workbook(_book(), source_name="01_04_A_New_loans_corp_20190201.xlsx")
    assert parsed.report_date == "2019-02-01"
    assert parsed.reference_period == "2019-01"
    assert len(parsed.sheets) == 3
    assert len(parsed.industries) == 26
    assert len(parsed.regions) == 96
    assert parsed.rows_stream == 96 * 26 * 3
    first = parsed.df_stream.loc[
        parsed.df_stream["region_code"].eq("0105a_region_001")
        & parsed.df_stream["industry_code"].eq("total")
        & parsed.df_stream["currency_scope"].eq("total")
    ]
    assert first["value"].iloc[0] == 3000
    assert first["reference_period"].iloc[0] == "2019-01"
    assert all(item.severity != "error" for item in parsed.validation_issues)


@pytest.mark.parametrize("kwargs", [
    {"date_text": "Февраль 2019"},
    {"wrong_industry": True},
    {"swapped_geography": True},
])
def test_parser_fails_closed_on_semantic_changes(kwargs) -> None:
    with pytest.raises(ValueError):
        parse_workbook(_book(**kwargs), source_name="01_04_A_New_loans_corp_20190201.xlsx")


def test_parser_retains_missing_value_and_rejects_negative() -> None:
    parsed = parse_workbook(_book(blank_component=True), source_name=_request().source_name)
    assert any(issue.code == "missing_values" for issue in parsed.validation_issues)
    result = issuance.parse(_request(_book(negative=True)))
    assert result.outcome == "failed"
    assert result.value is not None
    assert any(issue.code == "negative_values" for issue in result.value.validation_issues)


def test_missing_apk_component_prevents_rendering() -> None:
    result = issuance.build_stream(issuance.BuildIssuanceStreamRequest((_request(_book(blank_component=True)),)))
    assert result.outcome == "succeeded"
    rendering = issuance.render_industry(issuance.IssuanceWorkbookRequest(result.value, "apk"))
    assert rendering.outcome == "failed"


def test_history_preserves_month_and_rejects_duplicates() -> None:
    history = _history()
    assert history.dates == ("2019-02-01",)
    assert history.reference_periods == ("2019-01",)
    assert len(history.df_stream) == 96 * 26 * 3
    duplicated = issuance.build_stream(issuance.BuildIssuanceStreamRequest((_request(), _request())))
    assert duplicated.outcome == "failed"


def test_apk_reuses_shared_formula_for_issuance() -> None:
    history = _history()
    result = issuance.calculate_apk(issuance.CalculateIssuanceApkRequest(history.df_stream))
    assert result.outcome == "succeeded", result.diagnostics
    frame = result.value.df_stream
    apk = frame.loc[
        frame["industry_code"].astype("object").eq("apk")
        & frame["region_code"].astype("object").eq("0105a_region_001")
        & frame["currency_scope"].astype("object").eq("total")
    ]
    assert apk["value"].iloc[0] == (30 + 20 + 3 + 5) * 3
    assert apk["reference_period"].iloc[0] == "2019-01"


def test_render_three_sheets_and_preserve_official_total() -> None:
    history = _history()
    for industry, expected in (("total", 3000), ("apk", 174)):
        rendered = issuance.render_industry(issuance.IssuanceWorkbookRequest(history, industry))
        assert rendered.outcome == "succeeded", rendered.diagnostics
        output = rendered.value
        assert output.ok
        assert output.reference_periods == ("2019-01",)
        workbook = load_workbook(BytesIO(output.representation.data), read_only=True, data_only=True)
        try:
            assert workbook.sheetnames == ["в рублях", "в инвалюте", "итого"]
            assert workbook["итого"]["B4"].value == expected
            assert workbook["итого"]["B3"].value == "01.2019"
        finally:
            workbook.close()


def test_render_optional_metadata_and_unknown_industry() -> None:
    history = _history()
    rendered = issuance.render_industry(issuance.IssuanceWorkbookRequest(
        history, "total", include_metadata_sheet=True))
    assert rendered.outcome == "succeeded"
    assert rendered.value.sheet_names[0] == "_Параметры"
    assert rendered.value.sheet_count == 3
    invalid = issuance.render_industry(issuance.IssuanceWorkbookRequest(history, "unknown"))
    assert invalid.outcome == "failed"


def test_public_issuance_chain_keeps_parents_and_accepts_layout_changes():
    from stratbox.macrobanks.cbr_industries import Cbr0105ADebtCorpPivotRequest, RenderPivotRequest, render_pivots

    original = _request()
    base = issuance.parse(original)
    workbook = load_workbook(BytesIO(original.payload.data))
    workbook.create_sheet("Справка")["A1"] = "Пояснения к публикации"
    workbook["foreign"].insert_rows(5)
    workbook["foreign"].insert_cols(4)
    workbook["foreign"]["D3"] = "Пояснение к строке"
    target = BytesIO()
    workbook.save(target)
    workbook.close()
    changed = replace(original, payload=SourcePayload(target.getvalue()))
    parsed = issuance.parse(changed)
    assert parsed.outcome == "succeeded", parsed.diagnostics
    assert parsed.value.unmapped_headers == (("foreign", "Пояснение к строке"),)
    keys = ["region_code", "currency_scope", "industry_code", "reference_period", "value"]
    assert parsed.value.df_stream[keys].equals(base.value.df_stream[keys])
    history = issuance.build_stream(issuance.BuildIssuanceStreamRequest((changed,)))
    assert history.outcome == "succeeded", history.diagnostics
    calculated = issuance.calculate_apk(issuance.CalculateIssuanceApkRequest(history.value))
    assert calculated.outcome == "succeeded", calculated.diagnostics
    pivot = Cbr0105ADebtCorpPivotRequest(
        "region_code", "report_date", sheet_dimensions=("currency_scope",),
    )
    tables = issuance.build_pivots(issuance.PivotIssuanceRequest(calculated.value, pivot, industry_code="apk"))
    assert tables.outcome == "succeeded", tables.diagnostics
    rendered = render_pivots(RenderPivotRequest(tables.value))
    assert rendered.outcome == "succeeded", rendered.diagnostics
    receipt = rendered.computation
    for _ in range(3):
        receipt = receipt.parents[0][1]
    assert receipt.inputs[0].identity == changed.payload.identity
    calculated.value.df_stream.loc[calculated.value.df_stream.index[0], "value"] = 999
    rejected = issuance.build_pivots(issuance.PivotIssuanceRequest(calculated.value, pivot, industry_code="apk"))
    assert rejected.diagnostics[0].code == "input.identity_mismatch"
