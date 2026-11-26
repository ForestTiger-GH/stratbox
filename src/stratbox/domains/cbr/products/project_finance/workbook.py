"""Prepared workbook rendering."""

from __future__ import annotations

from numbers import Number

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

from stratbox.domains.cbr.products.specifications import Sheet


HEADER_FONT = Font(name="Arial", size=10, bold=True, color="000000")
DATA_FONT = Font(name="Arial", size=10)
FIRST_COL_FONT = Font(name="Arial", size=10, bold=True)
HEADER_FILL = PatternFill("solid", fgColor="BDD7EE")
PALE_GREEN_FILL = PatternFill("solid", fgColor="D8F5DC")
BORDER_STYLE = Side(border_style="thin", color="D3D3D3")
CELL_BORDER = Border(top=BORDER_STYLE, bottom=BORDER_STYLE, left=BORDER_STYLE, right=BORDER_STYLE)
WIDTH_FIRST_COL = 25
WIDTH_OTHER_COLS = 11


def build_escrow_workbook(
    pivots: dict[str, pd.DataFrame],
    indicator_specs: list[Sheet],
    *,
    title_row_font: Font | None = None,
    checkpoint=None,
    row_metadata=(),
) -> Workbook:
    """Render one prepared indicator table per configured sheet."""
    workbook = Workbook()
    workbook.remove(workbook.active)

    title_font = title_row_font or Font(name="Times New Roman", size=10, bold=True)
    used_sheet_names = set()
    row_kinds = {region: kind for region, kind, district in row_metadata}
    for spec in indicator_specs:
        if checkpoint is not None:
            checkpoint()
        pivot_df = pivots[spec.metric].reset_index()
        sheet_name = spec.name
        if sheet_name in used_sheet_names:
            raise ValueError(f"Duplicate escrow sheet code is detected: {sheet_name}")
        used_sheet_names.add(sheet_name)

        worksheet = workbook.create_sheet(title=sheet_name)
        worksheet["A2"] = str(spec.title).upper()
        worksheet["A2"].font = title_font

        rows = list(dataframe_to_rows(pivot_df, index=False, header=True))
        start_row = 4
        for row_idx, row in enumerate(rows, start_row):
            highlight_row = False
            if row_idx > start_row:
                region_value = str(row[0])
                if row_kinds.get(region_value) in {"federal_district", "rf_total"} or (not row_kinds and (" ФО" in region_value or "Итого по РФ" in region_value)):
                    highlight_row = True

            for col_idx, value in enumerate(row, 1):
                if value is not None and not isinstance(value, str) and pd.isna(value):
                    value = None
                cell = worksheet.cell(row=row_idx, column=col_idx, value=value)

                if row_idx == start_row:
                    cell.font = HEADER_FONT
                    cell.fill = HEADER_FILL
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.font = DATA_FONT
                    cell.alignment = Alignment(
                        horizontal="right" if col_idx > 1 else "left",
                        vertical="center",
                    )
                    if col_idx == 1:
                        cell.font = FIRST_COL_FONT
                    if col_idx > 1 and pd.notnull(value):
                        if isinstance(value, Number):
                            cell.number_format = spec.number_format
                    if highlight_row:
                        cell.fill = PALE_GREEN_FILL

                cell.border = CELL_BORDER

        for col_idx in range(1, worksheet.max_column + 1):
            col_letter = get_column_letter(col_idx)
            worksheet.column_dimensions[col_letter].width = (
                WIDTH_FIRST_COL if col_idx == 1 else WIDTH_OTHER_COLS
            )

        worksheet.freeze_panes = "B5"
        worksheet.sheet_view.showGridLines = False

    return workbook


__all__ = ["build_escrow_workbook"]
