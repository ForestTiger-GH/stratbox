"""Минимальный Excel-экспорт готового pivot-набора ``01_05_A_Debt_corp``."""

from __future__ import annotations

import math
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpPivotSetResult,
    Cbr0105ADebtCorpPivotWorkbookRequest,
    Cbr0105ADebtCorpPivotWorkbookResult,
)
from stratbox.macrobanks.cbr_industries.pivots import sanitize_excel_sheet_name


_HEADER_FILL = PatternFill(fill_type="solid", fgColor="D9EAF7")
_HEADER_FONT = Font(bold=True)
_THIN_GRAY = Side(style="thin", color="B7C3CF")
_HEADER_BORDER = Border(bottom=_THIN_GRAY)


def _normalize_xlsx_path(path: str) -> str:
    text = str(path).strip()
    if not text:
        raise ValueError("Pivot workbook output path is empty")
    return text if text.lower().endswith(".xlsx") else f"{text}.xlsx"


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


def _workbook_bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def save_cbr_0105a_debt_corp_pivot_workbook(
    pivot_set: Cbr0105ADebtCorpPivotSetResult,
    request: Cbr0105ADebtCorpPivotWorkbookRequest,
    *,
    filestore: FileStore | None = None,
) -> Cbr0105ADebtCorpPivotWorkbookResult:
    """Сохраняет все pivot-таблицы отдельными листами одной XLSX-книги."""
    if not pivot_set.tables:
        raise ValueError("Pivot set contains no tables")
    store = filestore or get_filestore()
    output_path = _normalize_xlsx_path(request.out_path)
    if store.exists(output_path) and not request.overwrite:
        raise FileExistsError(f"Pivot workbook already exists: {output_path}")

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
        content = _workbook_bytes(workbook)
    finally:
        workbook.close()

    store.write_bytes(output_path, content)
    sheet_names = tuple(
        (["_Параметры"] if request.include_metadata_sheet else [])
        + [table.suggested_sheet_name for table in pivot_set.tables]
    )
    return Cbr0105ADebtCorpPivotWorkbookResult(
        output_path=output_path,
        sheet_names=sheet_names,
        sheet_count=len(sheet_names),
        file_size=len(content),
        sha256=sha256(content).hexdigest(),
    )


__all__ = ["save_cbr_0105a_debt_corp_pivot_workbook"]
