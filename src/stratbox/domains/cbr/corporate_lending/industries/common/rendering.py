"""Source-independent CBR industry workbook cell and grid formatting.

Both 01_05_A debt stocks and 01_04_A monthly issuance use the same physical
region-by-date sheet renderer. Series-specific titles, measures, time semantics
and workbook metadata remain in their owning publication modules.
"""

from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def _excel_value(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, (date, datetime, str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    item = getattr(value, "item", None)
    if callable(item):
        return _excel_value(item())
    return str(value)



_CBR_FONT_NAME = "Times New Roman"
_CBR_TITLE_FONT = Font(name=_CBR_FONT_NAME, size=20, color="333333")
_CBR_SUBTITLE_FONT = Font(name=_CBR_FONT_NAME, size=12, color="333333")
_CBR_HEADER_FONT = Font(name=_CBR_FONT_NAME, size=12, bold=True, color="000000")
_CBR_BODY_FONT = Font(name=_CBR_FONT_NAME, size=12, color="000000")
_CBR_BOLD_FONT = Font(name=_CBR_FONT_NAME, size=12, bold=True, color="000000")
_CBR_COUNTRY_FILL = PatternFill(fill_type="solid", fgColor="CEFFFF")
_CBR_WHITE_FILL = PatternFill(fill_type="solid", fgColor="FFFFFF")
_CBR_BLACK_SIDE = Side(style="thin", color="000000")
_CBR_CELL_BORDER = Border(
    left=_CBR_BLACK_SIDE,
    right=_CBR_BLACK_SIDE,
    top=_CBR_BLACK_SIDE,
    bottom=_CBR_BLACK_SIDE,
)
_CBR_SUBTITLE_BORDER = Border(bottom=_CBR_BLACK_SIDE)
_CBR_NUMBER_FORMAT = "#,##0;\\-#,##0;0"


def _format_report_date(value: object) -> str:
    parsed = pd.to_datetime(value, errors="raise")
    return parsed.strftime("%d.%m.%Y")



def _industry_table_dates(table: object) -> tuple[str, ...]:
    if table.data_columns < 1:
        raise ValueError("Industry workbook pivot contains no date columns")
    columns = list(table.df_table.columns)
    date_columns = columns[-table.data_columns :]
    if any(isinstance(column, tuple) for column in date_columns):
        raise ValueError("Industry workbook supports exactly one numeric value column")
    return tuple(str(column) for column in date_columns)


def _write_cbr_industry_sheet(
    workbook: Workbook,
    *,
    table: object,
    sheet_name: str,
    title: str,
    subtitle: str,
    dates: tuple[str, ...],
) -> None:
    worksheet = workbook.create_sheet(title=sheet_name)
    worksheet.sheet_view.showGridLines = False
    worksheet.freeze_panes = "B4"

    dataframe = table.df_table
    required = {"region_name", "region_kind"}
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"Industry workbook table misses region descriptors: {missing}")

    last_column = 1 + len(dates)
    last_column_letter = get_column_letter(last_column)
    worksheet.merge_cells(f"A1:{last_column_letter}1")
    worksheet.merge_cells(f"A2:{last_column_letter}2")

    worksheet["A1"] = title
    if len(dates) < 5:
        title_font = Font(name=_CBR_FONT_NAME, size=12, color="333333")
        title_row_height = 78
    elif len(dates) < 12:
        title_font = Font(name=_CBR_FONT_NAME, size=14, color="333333")
        title_row_height = 47
    else:
        title_font = _CBR_TITLE_FONT
        title_row_height = 31.5
    worksheet["A1"].font = title_font
    worksheet["A1"].alignment = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=True,
    )
    worksheet["A1"].fill = _CBR_WHITE_FILL

    worksheet["A2"] = subtitle
    worksheet["A2"].font = _CBR_SUBTITLE_FONT
    worksheet["A2"].alignment = Alignment(horizontal="center", vertical="center")
    worksheet["A2"].fill = _CBR_WHITE_FILL
    for cell in worksheet[2]:
        cell.border = _CBR_SUBTITLE_BORDER

    worksheet["A3"] = None
    for column_index, report_date in enumerate(dates, start=2):
        worksheet.cell(3, column_index, _format_report_date(report_date))

    for column_index in range(1, last_column + 1):
        cell = worksheet.cell(3, column_index)
        cell.font = _CBR_HEADER_FONT
        cell.fill = _CBR_WHITE_FILL
        cell.border = _CBR_CELL_BORDER
        cell.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)

    columns = list(dataframe.columns)
    region_name_index = columns.index("region_name")
    region_kind_index = columns.index("region_kind")
    data_start_index = len(columns) - table.data_columns
    for row_offset, row_values in enumerate(
        dataframe.itertuples(index=False, name=None),
        start=4,
    ):
        region_name = _excel_value(row_values[region_name_index])
        region_kind = str(row_values[region_kind_index])
        worksheet.cell(row_offset, 1, region_name)
        for column_index, value in enumerate(
            row_values[data_start_index:],
            start=2,
        ):
            worksheet.cell(row_offset, column_index, _excel_value(value))

        is_country = region_kind == "country_total"
        is_district = region_kind == "federal_district_total"
        row_font = _CBR_BOLD_FONT if is_country or is_district else _CBR_BODY_FONT
        row_fill = _CBR_COUNTRY_FILL if is_country else _CBR_WHITE_FILL
        for column_index in range(1, last_column + 1):
            cell = worksheet.cell(row_offset, column_index)
            cell.font = row_font
            cell.fill = row_fill
            cell.border = _CBR_CELL_BORDER
            cell.alignment = Alignment(
                horizontal="left" if column_index == 1 else "right",
                vertical="center",
                wrap_text=(column_index == 1),
            )
            if column_index > 1:
                cell.number_format = _CBR_NUMBER_FORMAT

        region_text = str(region_name or "")
        worksheet.row_dimensions[row_offset].height = (
            42.2 if is_district or len(region_text) > 58 else 27.75
        )

    worksheet.row_dimensions[1].height = title_row_height
    worksheet.row_dimensions[2].height = 20.85
    worksheet.row_dimensions[3].height = 27.75
    worksheet.column_dimensions["A"].width = 37
    for column_index in range(2, last_column + 1):
        worksheet.column_dimensions[get_column_letter(column_index)].width = 13.5

    worksheet.page_setup.orientation = "landscape"
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.print_title_rows = "1:3"
    worksheet.auto_filter.ref = None


