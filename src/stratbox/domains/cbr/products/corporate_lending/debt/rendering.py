"""Минимальный Excel-экспорт готового pivot-набора ``01_05_A_Debt_corp``."""

from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
from stratbox.shared.data.values import EncodedProduct
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _excel_value
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _format_report_date
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _industry_table_dates
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _write_cbr_industry_sheet
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _CBR_HEADER_FONT
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _CBR_COUNTRY_FILL
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _CBR_CELL_BORDER
from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _CBR_BODY_FONT
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookRequest
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult as Cbr0105ADebtCorpPivotSetResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotTable as Cbr0105ADebtCorpPivotTable
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpPivotWorkbookRequest
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpPivotWorkbookResult
from stratbox.domains.cbr.products.corporate_lending.industry.views import sanitize_excel_sheet_name
from stratbox.domains.cbr.methods.tables.corporate_lending.debt.schema import CBR_0105A_DEBT_CORP_SHEET_SPECS
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import CBR_0105A_DEBT_CORP_UNIT_NAME_RU


_HEADER_FILL = PatternFill(fill_type="solid", fgColor="D9EAF7")
_HEADER_FONT = Font(bold=True)
_THIN_GRAY = Side(style="thin", color="B7C3CF")
_HEADER_BORDER = Border(bottom=_THIN_GRAY)


def _header_parts(column: object) -> tuple[str, str | None]:
    if isinstance(column, tuple):
        first = "" if column[0] is None else str(column[0])
        second = "" if len(column) < 2 or column[1] is None else str(column[1])
        return first, second
    return str(column), None


def _write_pivot_table_sheet(
    workbook: Workbook,
    *,
    sheet_name: str,
    table,
    freeze_headers: bool,
    enable_auto_filter: bool,
    adjust_column_widths: bool,
) -> None:
    worksheet = workbook.create_sheet(title=sanitize_excel_sheet_name(sheet_name))
    worksheet.sheet_view.showGridLines = False
    dataframe = table.df_table
    columns = list(dataframe.columns)
    descriptor_count = max(0, len(columns) - table.data_columns)
    multi_header = any(isinstance(column, tuple) for column in columns)
    header_rows = 2 if multi_header else 1

    for column_index, column in enumerate(columns, start=1):
        first, second = _header_parts(column)
        worksheet.cell(1, column_index, first)
        if header_rows == 2:
            worksheet.cell(2, column_index, second if second is not None else first)

    data_start_row = header_rows + 1
    for row_offset, row in enumerate(dataframe.itertuples(index=False, name=None), start=0):
        excel_row = data_start_row + row_offset
        for column_index, value in enumerate(row, start=1):
            worksheet.cell(excel_row, column_index, _excel_value(value))

    for row in range(1, header_rows + 1):
        for cell in worksheet[row]:
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.border = _HEADER_BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    if header_rows == 2:
        worksheet.row_dimensions[1].height = 24
        worksheet.row_dimensions[2].height = 24
    else:
        worksheet.row_dimensions[1].height = 24

    last_row = max(header_rows, header_rows + len(dataframe))
    last_column = max(1, len(columns))
    if enable_auto_filter and columns:
        worksheet.auto_filter.ref = (
            f"A{header_rows}:{get_column_letter(last_column)}{last_row}"
        )

    if freeze_headers and columns:
        freeze_column = min(descriptor_count + 1, last_column)
        worksheet.freeze_panes = f"{get_column_letter(freeze_column)}{data_start_row}"

    for column_index in range(descriptor_count + 1, last_column + 1):
        for row in range(data_start_row, last_row + 1):
            worksheet.cell(row, column_index).number_format = "#,##0.##"

    if adjust_column_widths:
        for column_index, column in enumerate(columns, start=1):
            header_first, header_second = _header_parts(column)
            sample_lengths = [len(header_first), len(header_second or "")]
            for row in range(data_start_row, min(last_row, data_start_row + 199) + 1):
                value = worksheet.cell(row, column_index).value
                if value is not None:
                    sample_lengths.append(len(str(value)))
            width = max(sample_lengths, default=8) + 2
            if column_index <= descriptor_count:
                width = min(max(width, 12), 42)
            else:
                width = min(max(width, 11), 18)
            worksheet.column_dimensions[get_column_letter(column_index)].width = width


def _write_metadata_sheet(workbook: Workbook, pivot_set: Cbr0105ADebtCorpPivotSetResult) -> None:
    worksheet = workbook.create_sheet(title="_Параметры", index=0)
    rows: list[tuple[str, object]] = [
        ("row_dimension", pivot_set.row_dimension),
        ("column_dimension", pivot_set.column_dimension),
        ("value_columns", ", ".join(pivot_set.value_columns)),
        ("sheet_dimensions", ", ".join(pivot_set.sheet_dimensions)),
        ("source_rows", pivot_set.source_rows),
        ("table_count", pivot_set.table_count),
        ("is_partial", pivot_set.is_partial),
    ]
    rows.extend((f"fixed:{name}", value) for name, value in pivot_set.fixed_dimensions)
    worksheet.append(["Параметр", "Значение"])
    for name, value in rows:
        worksheet.append([name, _excel_value(value)])
    for cell in worksheet[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _HEADER_BORDER
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:B{worksheet.max_row}"
    worksheet.column_dimensions["A"].width = 28
    worksheet.column_dimensions["B"].width = 40


def render_cbr_0105a_debt_corp_pivot_workbook(
    pivot_set: Cbr0105ADebtCorpPivotSetResult,
    request: Cbr0105ADebtCorpPivotWorkbookRequest, *, budget=None,
) -> Cbr0105ADebtCorpPivotWorkbookResult:
    """Сохраняет все pivot-таблицы отдельными листами одной XLSX-книги."""
    if not pivot_set.tables:
        raise ValueError("Pivot set contains no tables")
    workbook = Workbook()
    workbook.remove(workbook.active)
    try:
        if request.include_metadata_sheet:
            _write_metadata_sheet(workbook, pivot_set)
        for table in pivot_set.tables:
            _write_pivot_table_sheet(
                workbook,
                sheet_name=table.suggested_sheet_name,
                table=table,
                freeze_headers=request.freeze_headers,
                enable_auto_filter=request.enable_auto_filter,
                adjust_column_widths=request.adjust_column_widths,
            )
        content = openpyxl_bytes(workbook, literal_text=True, budget=budget)
    finally:
        workbook.close()

    sheet_names = tuple(
        (["_Параметры"] if request.include_metadata_sheet else [])
        + [table.suggested_sheet_name for table in pivot_set.tables]
    )
    return Cbr0105ADebtCorpPivotWorkbookResult(
        representation=EncodedProduct(content, XLSX),
        sheet_names=sheet_names,
        sheet_count=len(sheet_names),
        source_uses=pivot_set.source_uses,
    )


def _industry_sheet_title(
    *,
    industry_code: str,
    industry_name_ru: str,
    measure_name_ru: str,
    currency_scope: str,
    currency_scope_name_ru: str,
) -> str:
    currency_fragment = ""
    if currency_scope != "total":
        currency_fragment = f" {currency_scope_name_ru.lower()}"
    if industry_code == "apk":
        subject_fragment = f"по отраслевому агрегату «{industry_name_ru}»"
    elif industry_code == "total":
        subject_fragment = (
            "всего по видам экономической деятельности и отдельным "
            "направлениям использования средств"
        )
    else:
        subject_fragment = (
            f"по виду экономической деятельности «{industry_name_ru}»"
        )
    return (
        f"{measure_name_ru} по кредитам, предоставленным юридическим лицам - "
        f"резидентам и индивидуальным предпринимателям, {subject_fragment}"
        f"{currency_fragment}, в региональном разрезе, "
        f"{CBR_0105A_DEBT_CORP_UNIT_NAME_RU}"
    )


def _industry_period_subtitle(dates: tuple[str, ...]) -> str:
    if not dates:
        raise ValueError("Industry workbook contains no report dates")
    if len(dates) == 1:
        return f"Данные по состоянию на {_format_report_date(dates[0])}"
    return (
        "Динамика по состоянию на отчетные даты с "
        f"{_format_report_date(dates[0])} по {_format_report_date(dates[-1])}"
    )


def _table_key(table: Cbr0105ADebtCorpPivotTable) -> tuple[str, str]:
    values = dict(table.sheet_key)
    try:
        return str(values["measure"]), str(values["currency_scope"])
    except KeyError as exc:
        raise ValueError(
            "Industry workbook pivot must be split by measure and currency_scope"
        ) from exc


def _write_industry_metadata_sheet(
    workbook: Workbook,
    *,
    industry_code: str,
    industry_name_ru: str,
    dates: tuple[str, ...],
) -> None:
    worksheet = workbook.create_sheet(title="_Параметры", index=0)
    rows = [
        ("Серия", "01_05_A_Debt_corp"),
        ("Код отрасли", industry_code),
        ("Наименование отрасли", industry_name_ru),
        ("Первая отчетная дата", dates[0]),
        ("Последняя отчетная дата", dates[-1]),
        ("Количество отчетных дат", len(dates)),
        ("Единица измерения", CBR_0105A_DEBT_CORP_UNIT_NAME_RU),
    ]
    worksheet.append(["Параметр", "Значение"])
    for name, value in rows:
        worksheet.append([name, value])
    for cell in worksheet[1]:
        cell.font = _CBR_HEADER_FONT
        cell.fill = _CBR_COUNTRY_FILL
        cell.border = _CBR_CELL_BORDER
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=1, max_col=2):
        for cell in row:
            cell.font = _CBR_BODY_FONT
            cell.border = _CBR_CELL_BORDER
    worksheet.column_dimensions["A"].width = 30
    worksheet.column_dimensions["B"].width = 56
    worksheet.freeze_panes = "A2"
    worksheet.sheet_view.showGridLines = False


def render_cbr_0105a_debt_corp_industry_workbook(
    pivot_set: Cbr0105ADebtCorpPivotSetResult,
    request: Cbr0105ADebtCorpIndustryWorkbookRequest,
    *,
    industry_name_ru: str,
    budget=None,
) -> Cbr0105ADebtCorpIndustryWorkbookResult:
    """Сохраняет динамику одной отрасли по регионам в стиле публикации Банка России."""
    if pivot_set.row_dimension != "region_code" or pivot_set.column_dimension != "report_date":
        raise ValueError(
            "Industry workbook requires row_dimension='region_code' and "
            "column_dimension='report_date'"
        )
    if pivot_set.value_columns != ("value",):
        raise ValueError("Industry workbook requires exactly value_columns=('value',)")
    if set(pivot_set.sheet_dimensions) != {"measure", "currency_scope"}:
        raise ValueError(
            "Industry workbook requires sheet_dimensions measure and currency_scope"
        )
    if pivot_set.table_count != 6:
        raise ValueError(
            f"Industry workbook requires six tables, actual={pivot_set.table_count}"
        )

    tables_by_key = {_table_key(table): table for table in pivot_set.tables}
    expected_keys = {
        (spec.measure, spec.currency_scope)
        for spec in CBR_0105A_DEBT_CORP_SHEET_SPECS
    }
    if set(tables_by_key) != expected_keys:
        raise ValueError(
            "Industry workbook table set differs from the six source indicators"
        )

    ordered_specs = tuple(sorted(CBR_0105A_DEBT_CORP_SHEET_SPECS, key=lambda item: item.order))
    first_table = tables_by_key[(ordered_specs[0].measure, ordered_specs[0].currency_scope)]
    dates = _industry_table_dates(first_table)
    if any(_industry_table_dates(table) != dates for table in tables_by_key.values()):
        raise ValueError("Industry workbook sheets contain different report dates")

    workbook = Workbook()
    workbook.remove(workbook.active)
    try:
        if request.include_metadata_sheet:
            _write_industry_metadata_sheet(
                workbook,
                industry_code=request.industry_code,
                industry_name_ru=industry_name_ru,
                dates=dates,
            )
        subtitle = _industry_period_subtitle(dates)
        for spec in ordered_specs:
            table = tables_by_key[(spec.measure, spec.currency_scope)]
            _write_cbr_industry_sheet(
                workbook,
                table=table,
                sheet_name=spec.workbook_sheet_name,
                title=_industry_sheet_title(
                    industry_code=request.industry_code,
                    industry_name_ru=industry_name_ru,
                    measure_name_ru=spec.measure_name_ru,
                    currency_scope=spec.currency_scope,
                    currency_scope_name_ru=spec.currency_scope_name_ru,
                ),
                subtitle=subtitle,
                dates=dates,
            )
        content = openpyxl_bytes(workbook, literal_text=True, budget=budget)
    finally:
        workbook.close()

    sheet_names = tuple(
        (["_Параметры"] if request.include_metadata_sheet else [])
        + [spec.workbook_sheet_name for spec in ordered_specs]
    )
    rows_per_sheet = first_table.rows
    return Cbr0105ADebtCorpIndustryWorkbookResult(
        representation=EncodedProduct(content, XLSX),
        industry_code=request.industry_code,
        industry_name_ru=industry_name_ru,
        sheet_names=sheet_names,
        sheet_count=len(sheet_names) - (1 if request.include_metadata_sheet else 0),
        dates=dates,
        rows_per_sheet=rows_per_sheet,
        source_uses=pivot_set.source_uses,
    )


__all__ = [
    "render_cbr_0105a_debt_corp_industry_workbook",
    "render_cbr_0105a_debt_corp_pivot_workbook",
]
