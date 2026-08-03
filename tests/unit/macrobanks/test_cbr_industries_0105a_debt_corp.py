from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from stratbox.base.filestore import LocalFileStore
from stratbox.macrobanks.cbr_industries import (
    CBR_0105A_DEBT_CORP_INDUSTRY_SPECS,
    CBR_SORS_INDEX_URL,
    Cbr0105ADebtCorpDownloadBatchResult,
    Cbr0105ADebtCorpDownloadedSource,
    Cbr0105ADebtCorpStreamBuildRequest,
    build_cbr_0105a_debt_corp_stream,
    parse_cbr_0105a_debt_corp_excel_bytes,
)
from stratbox.macrobanks.cbr_industries.download import (
    try_download_cbr_0105a_debt_corp_source,
)
from stratbox.macrobanks.cbr_industries.regions import (
    normalize_cbr_0105a_debt_corp_regions_to_latest,
)
from stratbox.macrobanks.cbr_industries.sources import (
    Cbr0105ADebtCorpSourceLink,
    discover_cbr_0105a_debt_corp_links_from_html,
)


SHEETS = (
    (
        "rub",
        "Задолженность по кредитам, предоставленным юридическим лицам - резидентам и индивидуальным предпринимателям в рублях, по видам экономической деятельности и отдельным направлениям использования средств, млн руб.",
        10,
    ),
    (
        " overdue,rub ",
        "Просроченная задолженность по кредитам, предоставленным юридическим лицам - резидентам и индивидуальным предпринимателям в рублях, по видам экономической деятельности и отдельным направлениям использования средств, млн руб.",
        1,
    ),
    (
        "foreign",
        "Задолженность по кредитам, предоставленным юридическим лицам - резидентам и индивидуальным предпринимателям в иностранной валюте и драгоценных металлах, по видам экономической деятельности и отдельным направлениям использования средств, млн руб.",
        5,
    ),
    (
        " overdue foreign ",
        "Просроченная задолженность по кредитам, предоставленным юридическим лицам - резидентам и индивидуальным предпринимателям в иностранной валюте и драгоценных металлах, по видам экономической деятельности и отдельным направлениям использования средств, млн руб.",
        2,
    ),
    (
        "total",
        "Задолженность по кредитам, предоставленным юридическим лицам - резидентам и индивидуальным предпринимателям, по видам экономической деятельности и отдельным направлениям использования средств, млн руб.",
        15,
    ),
    (
        " overdue total ",
        "Просроченная задолженность по кредитам, предоставленным юридическим лицам - резидентам и индивидуальным предпринимателям, по видам экономической деятельности и отдельным направлениям использования средств, млн руб.",
        3,
    ),
)


def _workbook_bytes(*, report_date: str, kemerovo_name: str) -> bytes:
    day, month, year = report_date.split(".")
    filename_date = f"{year}{month}{day}"
    assert len(filename_date) == 8

    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, title, base_value in SHEETS:
        sheet = workbook.create_sheet(sheet_name)
        sheet.cell(1, 1, title)
        sheet.cell(2, 1, f"Задолженность по кредитам по состоянию на {report_date}")
        for column, spec in enumerate(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS, start=2):
            source_header = spec.canonical_name_ru
            if spec.hierarchy_level > 1:
                source_header = "_________\n" * (spec.hierarchy_level - 1) + source_header
            if spec.code in {
                "mining",
                "manufacturing",
                "manufacturing_machinery_equipment",
                "manufacturing_transport_equipment",
                "agriculture_hunting_forestry",
                "construction",
                "transport_communications",
            }:
                source_header += ", из них:"
            sheet.cell(3, column, source_header)
        sheet.cell(4, 1, "РОССИЙСКАЯ ФЕДЕРАЦИЯ")
        sheet.cell(5, 1, "СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ")
        sheet.cell(6, 1, kemerovo_name)
        for row in range(4, 7):
            for column in range(2, 28):
                value = base_value
                if row == 6 and column == 2 and base_value == 1:
                    value = "0"
                sheet.cell(row, column, value)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_discovery_filters_exact_series_and_period() -> None:
    html = b"""
    <a href="/vfs/statistics/BankSector/Loans_to_corporations/01_05_A_Debt_corp_20260401.xlsx">a</a>
    <a href="/vfs/statistics/BankSector/Loans_to_corporations/01_05_A_Debt_corp_20260501.xlsx">b</a>
    <a href="/vfs/statistics/BankSector/Loans_to_corporations/01_05_A_Debt_corp_20260601.xlsx">c</a>
    <a href="/vfs/statistics/BankSector/Loans_to_corporations/01_05_A_Loans_corp_20260601.xlsx">other</a>
    """
    links = discover_cbr_0105a_debt_corp_links_from_html(
        html,
        date_from="2026-05-01",
        date_to="2026-06-01",
    )
    assert [item.report_date for item in links] == ["2026-05-01", "2026-06-01"]
    assert all(item.source_name.startswith("01_05_A_Debt_corp_") for item in links)


def test_parser_recognizes_sheets_by_title_and_builds_full_stream() -> None:
    content = _workbook_bytes(report_date="01.06.2026", kemerovo_name="Кемеровская область - Кузбасс")
    parsed = parse_cbr_0105a_debt_corp_excel_bytes(
        content,
        source_name="01_05_A_Debt_corp_20260601.xlsx",
    )

    assert parsed.report_date == "2026-06-01"
    assert parsed.rows_stream == 6 * 3 * 26
    assert [item.code for item in parsed.sheets] == [
        "debt_rubles",
        "overdue_debt_rubles",
        "debt_foreign_currency_and_precious_metals",
        "overdue_debt_foreign_currency_and_precious_metals",
        "debt_total",
        "overdue_debt_total",
    ]
    zero_row = parsed.df_stream[
        (parsed.df_stream["region_source_name"] == "Кемеровская область - Кузбасс")
        & (parsed.df_stream["industry_code"] == "total")
        & (parsed.df_stream["sheet_code"] == "overdue_debt_rubles")
    ].iloc[0]
    assert zero_row["value"] == 0
    assert zero_row["source_column"] == "B"
    assert zero_row["source_row"] == 6


def test_region_names_are_normalized_to_latest_selected_date() -> None:
    old = parse_cbr_0105a_debt_corp_excel_bytes(
        _workbook_bytes(report_date="01.02.2019", kemerovo_name="Кемеровская область"),
        source_name="01_05_A_Debt_corp_20190201.xlsx",
    )
    latest = parse_cbr_0105a_debt_corp_excel_bytes(
        _workbook_bytes(report_date="01.06.2026", kemerovo_name="Кемеровская область - Кузбасс"),
        source_name="01_05_A_Debt_corp_20260601.xlsx",
    )

    normalized = normalize_cbr_0105a_debt_corp_regions_to_latest([old, latest])
    old_stream = normalized[0].df_stream
    row = old_stream[old_stream["region_source_name"] == "Кемеровская область"].iloc[0]
    assert row["region_name"] == "Кемеровская область - Кузбасс"
    assert normalized[0].regions[-1].source_name == "Кемеровская область"
    assert normalized[0].regions[-1].canonical_name == "Кемеровская область - Кузбасс"


def test_download_reads_valid_source_from_year_cache(tmp_path: Path) -> None:
    content = _workbook_bytes(report_date="01.06.2026", kemerovo_name="Кемеровская область - Кузбасс")
    source = Cbr0105ADebtCorpSourceLink(
        source_id="01_05_A_Debt_corp_20260601",
        url="https://example.invalid/01_05_A_Debt_corp_20260601.xlsx",
        source_name="01_05_A_Debt_corp_20260601.xlsx",
        report_date="2026-06-01",
    )
    store = LocalFileStore(root=str(tmp_path))
    cache_path = "cache/2026/01_05_A_Debt_corp_20260601.xlsx"
    store.write_bytes(cache_path, content)

    downloaded, failure = try_download_cbr_0105a_debt_corp_source(
        source,
        store=store,
        source_cache_dir="cache",
        refresh=False,
        timeout=1,
        retries=0,
        backoff=0,
        min_bytes_ok=512,
        headers=None,
        plugin_only=False,
    )
    assert failure is None
    assert downloaded is not None
    assert downloaded.from_cache is True
    assert downloaded.cache_path == cache_path
    assert downloaded.content == content


def test_build_stream_orchestrates_parse_and_latest_region_names(monkeypatch) -> None:
    old_content = _workbook_bytes(
        report_date="01.02.2019",
        kemerovo_name="Кемеровская область",
    )
    latest_content = _workbook_bytes(
        report_date="01.06.2026",
        kemerovo_name="Кемеровская область - Кузбасс",
    )
    links = (
        Cbr0105ADebtCorpSourceLink(
            source_id="01_05_A_Debt_corp_20190201",
            url="https://example.invalid/01_05_A_Debt_corp_20190201.xlsx",
            source_name="01_05_A_Debt_corp_20190201.xlsx",
            report_date="2019-02-01",
        ),
        Cbr0105ADebtCorpSourceLink(
            source_id="01_05_A_Debt_corp_20260601",
            url="https://example.invalid/01_05_A_Debt_corp_20260601.xlsx",
            source_name="01_05_A_Debt_corp_20260601.xlsx",
            report_date="2026-06-01",
        ),
    )
    downloaded = tuple(
        Cbr0105ADebtCorpDownloadedSource(
            source_id=link.source_id,
            url=link.url,
            source_name=link.source_name,
            report_date=link.report_date,
            content=content,
            size_bytes=len(content),
            sha256="test",
            used_url=link.url,
            final_url=link.url,
        )
        for link, content in zip(links, (old_content, latest_content), strict=True)
    )

    from stratbox.macrobanks.cbr_industries import operations

    monkeypatch.setattr(
        operations,
        "download_cbr_0105a_debt_corp_sources",
        lambda request, filestore=None: Cbr0105ADebtCorpDownloadBatchResult(
            source_links=links,
            downloaded_sources=downloaded,
            failures=(),
        ),
    )
    result = build_cbr_0105a_debt_corp_stream(
        Cbr0105ADebtCorpStreamBuildRequest(
            index_url=CBR_SORS_INDEX_URL,
            show_progress=False,
        )
    )

    assert result.ok
    assert result.latest_report_date == "2026-06-01"
    assert result.rows_stream == 2 * 6 * 3 * 26
    old_row = result.df_stream[
        (result.df_stream["report_date"] == "2019-02-01")
        & (result.df_stream["region_source_name"] == "Кемеровская область")
    ].iloc[0]
    assert old_row["region_name"] == "Кемеровская область - Кузбасс"
    assert str(result.df_stream["region_name"].dtype) == "category"
