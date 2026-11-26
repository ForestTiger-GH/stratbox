"""Offline deterministic release, parser, history, derived and workbook gates for 01_04_A."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.geography import CBR_0105A_DEBT_CORP_REGION_LAYOUT
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS
from stratbox.domains.cbr.methods.tables.corporate_lending.issuance.parser import parse_workbook
from stratbox.domains.cbr.methods.publications.corporate_lending.issuance import discover_links
from stratbox.domains.cbr.methods.publications.corporate_lending.issuance_rules import reference_period
from stratbox.domains.cbr.methods.publications.corporate_lending.issuance_rules import report_date_from_filename

def _render(history, industry_code, *, include_metadata_sheet=False):
    from stratbox.domains.cbr.calculations.industry.apk import calculate_cbr_0105a_debt_corp_apk_industry
    from stratbox.domains.cbr.products.corporate_lending.industry.views import build_cbr_0105a_debt_corp_pivot_set
    from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest
    from stratbox.domains.cbr.products.corporate_lending.issuance.rendering import render_issuance_workbook
    frame = history.df_stream
    if industry_code == "apk":
        frame = calculate_cbr_0105a_debt_corp_apk_industry(frame).df_stream
        name = "АПК"
    else:
        spec = next((x for x in history.industries if x.code == industry_code), None)
        if spec is None:
            raise ValueError("request.industry_unresolved")
        name = spec.canonical_name_ru
    selected = frame.loc[frame.industry_code.astype(object).eq(industry_code)].copy()
    pivots = build_cbr_0105a_debt_corp_pivot_set(selected, IndustryPivotRequest("region_code", "report_date", sheet_dimensions=("measure", "currency_scope")), stream_result=history)
    return render_issuance_workbook(pivots, industry_code=industry_code, industry_name_ru=name,
        reference_periods=history.reference_periods, include_metadata_sheet=include_metadata_sheet)


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


def _request(payload=None):
    from types import SimpleNamespace
    return SimpleNamespace(payload=SourcePayload(payload if payload is not None else _book()), source_name="01_04_A_New_loans_corp_20190201.xlsx")



def _history(content=None, selection=None):
    from stratbox.domains.cbr.methods.alignment.corporate_lending.issuance.contracts import IssuanceStreamResult
    from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySelection
    parsed = parse_workbook(content or _book(), source_name=_request().source_name, selection=selection or IndustrySelection())
    return IssuanceStreamResult((), (), (parsed,), parsed.validation_issues, parsed.df_stream,
        (parsed.report_date,), (parsed.reference_period,), parsed.report_date, parsed.report_date,
        parsed.report_date, True, parsed.regions, parsed.industries, len(parsed.df_stream), selection=parsed.selection)



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
    negative = parse_workbook(_book(negative=True), source_name=_request().source_name)
    assert any(issue.code == "negative_values" and issue.severity == "error" for issue in negative.validation_issues)



def test_missing_apk_component_prevents_rendering() -> None:
    from stratbox.domains.cbr.calculations.industry.apk import calculate_cbr_0105a_debt_corp_apk_industry, Cbr0105ADebtCorpDerivedIndustryError
    with pytest.raises(Cbr0105ADebtCorpDerivedIndustryError):
        calculate_cbr_0105a_debt_corp_apk_industry(_history(_book(blank_component=True)).df_stream)



def test_history_preserves_month_and_rejects_duplicates() -> None:
    from stratbox.domains.cbr.methods.tables.corporate_lending.debt.parser import concat_industry_streams
    from stratbox.domains.cbr.products.corporate_lending.industry.views import build_cbr_0105a_debt_corp_pivot_set, Cbr0105ADebtCorpPivotError
    from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest
    history = _history()
    assert history.dates == ("2019-02-01",)
    assert history.reference_periods == ("2019-01",)
    assert len(history.df_stream) == 96 * 26 * 3
    duplicated = concat_industry_streams((history.df_stream, history.df_stream))
    selected = duplicated.loc[duplicated.industry_code.eq("total")]
    with pytest.raises(Cbr0105ADebtCorpPivotError):
        build_cbr_0105a_debt_corp_pivot_set(selected, IndustryPivotRequest("region_code", "report_date", sheet_dimensions=("measure", "currency_scope")))



def test_apk_reuses_shared_formula_for_issuance() -> None:
    from stratbox.domains.cbr.calculations.industry.apk import calculate_cbr_0105a_debt_corp_apk_industry
    result = calculate_cbr_0105a_debt_corp_apk_industry(_history().df_stream)
    apk = result.df_stream.loc[result.df_stream.industry_code.eq("apk") & result.df_stream.region_code.eq("0105a_region_001") & result.df_stream.currency_scope.eq("total")]
    assert apk.value.iloc[0] == (30 + 20 + 3 + 5) * 3
    assert apk.reference_period.iloc[0] == "2019-01"



def test_render_three_sheets_and_preserve_official_total() -> None:
    history = _history()
    for industry, expected in (("total", 3000), ("apk", 174)):
        output = _render(history, industry)
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
    rendered = _render(history, "total", include_metadata_sheet=True)
    assert rendered.sheet_names[0] == "_Параметры"
    assert rendered.sheet_count == 3
    with pytest.raises(ValueError, match="industry_unresolved"):
        _render(history, "unknown")



def test_public_issuance_chain_keeps_parents_and_accepts_layout_changes():
    from stratbox.domains.cbr.methods.actions.industries import extract, interpret
    from stratbox.domains.cbr.calculations.industry.actions import calculate
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
    from stratbox.domains.cbr.domain import DOMAIN
    from stratbox.shared.data.values import Material, WorkbookEvidence
    from types import SimpleNamespace
    original = _request()
    base = parse_workbook(original.payload.data, source_name=original.source_name)
    workbook = load_workbook(BytesIO(original.payload.data))
    workbook.create_sheet("Справка")["A1"] = "Пояснения к публикации"
    workbook["foreign"].insert_rows(5); workbook["foreign"].insert_cols(4)
    workbook["foreign"]["D3"] = "Пояснение к строке"
    target = BytesIO(); workbook.save(target); workbook.close()
    parsed = parse_workbook(target.getvalue(), source_name=original.source_name)
    assert parsed.unmapped_headers == (("foreign", "Пояснение к строке"),)
    keys = ["region_code", "currency_scope", "industry_code", "reference_period", "value"]
    assert parsed.df_stream[keys].equals(base.df_stream[keys])
    material = Material(target.getvalue(), source_id="cbr.corporate_lending.issuance_0104a")
    context = SimpleNamespace(parameters={"source_name": original.source_name, "issue_id": "2019-02-01"}, checkpoint=lambda: None)
    commands = DOMAIN.series[material.source_id].commands
    tables = extract({"physical": WorkbookEvidence(material, read_workbook_cells(material.data))}, commands["command.table.extract"].settings, context)["tables"]
    source = interpret({"tables": tables}, commands["command.table.interpret"].settings, context)["dataset"]
    assert {row["period"] for row in source.rows} == {("2019-01-01", "2019-01-31")}
    result = calculate({"dataset": source}, DOMAIN.calculations["cbr.corporate_lending.issuance_apk"].commands["command.calculate.formula"].settings, context)["dataset"]
    assert material.identity in result.lineage
    assert all(len(row["operands"]) == 5 for row in result.rows)



def test_issuance_selected_observations_and_batch_export_match_individual() -> None:
    from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySelection
    full = _history()
    projection = _history(selection=IndustrySelection(("apk", "total")))
    assert projection.rows_stream == 96 * 6 * 3
    assert projection.selection.industry_codes == ("apk", "total")
    assert projection.source_validation_scope == "full"
    assert projection.reference_periods == ("2019-01",)
    assert full.validation_issues == projection.validation_issues
    codes = {"total", "agriculture_hunting_services", "agriculture_hunting_forestry", "manufacturing_food_beverages_tobacco", "manufacturing_machinery_agriculture_forestry", "manufacturing_wood_products"}
    cols = ["report_date", "reference_period", "region_code", "industry_code", "currency_scope", "value", "source_row", "source_column"]
    assert full.df_stream.loc[full.df_stream.industry_code.isin(codes), cols].astype(object).to_dict("records") == projection.df_stream[cols].astype(object).to_dict("records")
    for code in ("apk", "total"):
        assert _render(projection, code).representation.data == _render(full, code).representation.data



def test_issuance_source_validation_checks_outside_selected_industries() -> None:
    from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySelection
    result = parse_workbook(_book(negative=True), source_name=_request().source_name, selection=IndustrySelection(("total",)))
    assert result.source_validation_scope == "full"
    assert any(issue.code == "negative_values" and issue.severity == "error" for issue in result.validation_issues)
