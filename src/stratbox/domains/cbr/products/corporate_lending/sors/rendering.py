from __future__ import annotations

import math
import re
from dataclasses import asdict
from stratbox.core.storage.bytes import OutputBuffer
from stratbox.shared.data.values import EncodedProduct
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
from datetime import date, datetime
from typing import Any

import pandas as pd
import xlsxwriter

from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsWorkbookResult, SorsViewPack
from stratbox.domains.cbr.products.corporate_lending.sors.validation import validate_view_pack



def _excel_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return 'INF' if value > 0 else '-INF'
        return value
    if isinstance(value, (str, int, bool, datetime, date)):
        return value
    if hasattr(value, 'item'):
        try:
            return _excel_value(value.item())
        except Exception:
            pass
    if isinstance(value, (tuple, list, set, dict)):
        return str(value)
    return str(value)


def _widths(frame: pd.DataFrame) -> list[int]:
    sample = frame.head(200)
    widths: list[int] = []
    for column in frame.columns:
        values = sample[column].map(_excel_value).dropna().astype(str)
        maximum = max([len(str(column)), *(len(value) for value in values)], default=len(str(column)))
        widths.append(min(max(maximum + 2, 10), 48))
    return widths


def _write_frame(workbook, frame: pd.DataFrame, sheet: str, header_format, checkpoint) -> None:
    worksheet = workbook.add_worksheet(sheet)
    worksheet.freeze_panes(1, 0)
    worksheet.write_row(0, 0, list(frame.columns), header_format)
    for row_index, row in enumerate(frame.itertuples(index=False, name=None), start=1):
        if row_index % 1024 == 0:
            checkpoint()
        worksheet.write_row(row_index, 0, [_excel_value(value) for value in row])
    if len(frame.columns):
        worksheet.autofilter(0, 0, max(len(frame), 1), len(frame.columns) - 1)
    for column_index, width in enumerate(_widths(frame)):
        worksheet.set_column(column_index, column_index, width)


def render_sors_views(views: SorsViewPack, *, checkpoint=lambda: None, budget=None) -> SorsWorkbookResult:
    validate_view_pack(views)
    frames = views.tables
    if budget is not None:
        budget.charge("cells", sum((len(frame) + 1) * len(frame.columns) for _, frame in frames))
    output = OutputBuffer(budget)
    with xlsxwriter.Workbook(output, {"constant_memory": True, "strings_to_formulas": False,
                                      "strings_to_urls": False}) as workbook:
        workbook.set_properties({"created": datetime(1980, 1, 1)})
        header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        for sheet, frame in frames:
            checkpoint()
            _write_frame(workbook, frame, sheet, header_format, checkpoint)
    sheets = tuple(sheet for sheet, _ in frames)
    return SorsWorkbookResult(EncodedProduct(output.getvalue(), XLSX, (views.source_identity,) if views.source_identity else ()),
                              sheets, len(sheets))
