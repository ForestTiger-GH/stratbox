"""
Модуль формирует и экспортирует выходные файлы домена ``cbr_forms``.
"""

from __future__ import annotations

from copy import copy
from typing import Mapping

import pandas as pd

from stratbox.base.ioapi.workbook_bytes import openpyxl_bytes
from stratbox.base.styles.excel.main import apply_preset
from stratbox.macrobanks.cbr_forms.common.excel_profiles import (
    HIERARCHICAL_STATEMENT_PROFILE,
    STANDARD_PROFILE,
    build_hierarchical_statement_sheets,
)
from stratbox.macrobanks.cbr_forms.common.wide import build_wide_table


EXCEL_META = {
    "creator": "Center for Macroeconomic Analysis and Forecasting (CMAF)",
    "title": "Strategy Box Table Export",
    "category": "CMAF DATA",
}


def _set_workbook_meta(wb) -> None:
    """
    Функция записывает стандартные свойства книги Stratbox.
    """
    props = wb.properties
    props.creator = EXCEL_META["creator"]
    props.title = EXCEL_META["title"]
    props.category = EXCEL_META["category"]


def _set_column_widths(ws, widths: Mapping[str, float], *, date_width: float = 15.0) -> None:
    """
    Функция задает предсказуемые ширины колонок специализированной книги.
    """
    for cell in ws[1]:
        header = str(cell.value or "")
        width = widths.get(header)
        if width is None and header and header[0:2].isdigit() and "." in header:
            width = date_width
        if width is not None:
            ws.column_dimensions[cell.column_letter].width = float(width)


def _format_hierarchical_workbook(wb, sheets: dict[str, pd.DataFrame]) -> None:
    """
    Функция применяет оформление иерархической книги без изменения данных.
    """
    freeze = {
        "Обзор": "E2",
        "Полная форма": "F2",
        "Данные": "A2",
    }
    widths = {
        "Раздел": 22,
        "Код": 11,
        "Показатель": 58,
        "Банк": 25,
        "Уровень": 9,
        "Дата": 13,
        "REGN": 10,
        "IndicatorId": 18,
        "Форма": 9,
        "Порядок": 10,
        "РодительскийКод": 18,
        "Measure": 20,
        "Значение": 17,
        "Единица": 17,
    }

    for sheet_name, frame in sheets.items():
        ws = wb[sheet_name]
        apply_preset(ws, "DEFAULT", freeze_panes=freeze[sheet_name])
        if ws.max_row > 1 and ws.max_column > 0:
            ws.auto_filter.ref = ws.dimensions
        _set_column_widths(ws, widths)

        headers = {str(cell.value): cell.column for cell in ws[1]}
        if sheet_name in {"Обзор", "Полная форма"}:
            first_date_col = 5 if sheet_name == "Обзор" else 6
            for row in ws.iter_rows(min_row=2, min_col=first_date_col, max_col=ws.max_column):
                for cell in row:
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "#,##0"

        if sheet_name == "Данные" and "Значение" in headers:
            value_col = headers["Значение"]
            for row_idx in range(2, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=value_col)
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "#,##0"

        if sheet_name == "Полная форма":
            indicator_col = headers.get("Показатель")
            level_col = headers.get("Уровень")
            if indicator_col and level_col:
                ws.sheet_properties.outlinePr.summaryBelow = False
                for row_idx in range(2, ws.max_row + 1):
                    level = int(ws.cell(row=row_idx, column=level_col).value or 0)
                    indicator_cell = ws.cell(row=row_idx, column=indicator_col)
                    alignment = copy(indicator_cell.alignment)
                    alignment.indent = min(level, 15)
                    indicator_cell.alignment = alignment
                    ws.row_dimensions[row_idx].outlineLevel = min(level, 7)
                    if level == 0:
                        for cell in ws[row_idx]:
                            font = copy(cell.font)
                            font.bold = True
                            cell.font = font


def build_form_sheets(*, profile, df_long, df_banks, model_df, indicator_order):
    if profile == STANDARD_PROFILE:
        return {"data": build_wide_table(df_long=df_long, df_banks=df_banks,
                                         indicator_order=indicator_order)}
    if profile == HIERARCHICAL_STATEMENT_PROFILE:
        return build_hierarchical_statement_sheets(df_long=df_long, df_banks=df_banks, model_df=model_df)
    raise ValueError("Unknown form workbook profile")


def render_form_workbook(sheets, *, profile, budget=None):
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.remove(workbook.active)
    try:
        for name, frame in sheets.items():
            sheet = workbook.create_sheet(name)
            sheet.append([str(value) for value in frame.columns])
            for row in frame.itertuples(index=False, name=None):
                sheet.append([None if pd.isna(value) else value for value in row])
        _set_workbook_meta(workbook)
        if profile == HIERARCHICAL_STATEMENT_PROFILE:
            _format_hierarchical_workbook(workbook, sheets)
        else:
            sheet = workbook["data"]
            apply_preset(sheet, "DEFAULT")
            sheet.auto_filter.ref = sheet.dimensions
        return openpyxl_bytes(workbook, literal_text=True, budget=budget)
    finally:
        workbook.close()
