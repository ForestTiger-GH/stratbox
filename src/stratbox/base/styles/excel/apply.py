"""
Применение StyleSpec к openpyxl worksheet.

Комментарии — на русском (внешне, от третьего лица).
"""

from __future__ import annotations

from typing import Optional

from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .models import StyleSpec


def _apply_gridlines(ws: Worksheet, hide: bool) -> None:
    ws.sheet_view.showGridLines = not bool(hide)


def _apply_freeze(ws: Worksheet, freeze_rows: int, freeze_cols: int, freeze_panes: str | None) -> None:
    # Если пользователь явно передал freeze_panes, он важнее.
    if freeze_panes:
        ws.freeze_panes = freeze_panes
        return

    if freeze_rows <= 0 and freeze_cols <= 0:
        ws.freeze_panes = None
        return

    row = freeze_rows + 1 if freeze_rows > 0 else 1
    col = freeze_cols + 1 if freeze_cols > 0 else 1
    ws.freeze_panes = f"{get_column_letter(col)}{row}"


def _apply_font(ws: Worksheet, spec: StyleSpec) -> None:
    if not spec.font_theme:
        return

    theme = spec.font_theme
    header_font = Font(name=theme.name, size=theme.size, bold=theme.header_bold)
    body_font = Font(name=theme.name, size=theme.size, bold=False)

    max_row = ws.max_row or 1
    max_col = ws.max_column or 1

    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            if r <= spec.header_rows or c <= spec.header_cols:
                cell.font = header_font
            else:
                cell.font = body_font


def _apply_palette(ws: Worksheet, spec: StyleSpec) -> None:
    if not spec.palette:
        return

    pal = spec.palette

    fill_main = PatternFill("solid", fgColor=pal.header_fill_main)
    fill_side = PatternFill("solid", fgColor=pal.header_fill_side)
    header_font = None
    if spec.font_theme:
        header_font = Font(name=spec.font_theme.name, size=spec.font_theme.size, bold=spec.font_theme.header_bold, color=pal.header_font_color)
    else:
        header_font = Font(bold=True, color=pal.header_font_color)

    body_fill = PatternFill("solid", fgColor=pal.data_fill) if pal.data_fill else None

    max_row = ws.max_row or 1
    max_col = ws.max_column or 1

    # Заголовки: верхние строки и левые столбцы
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)

            is_top_header = r <= spec.header_rows
            is_left_header = c <= spec.header_cols

            if is_top_header and is_left_header:
                cell.fill = fill_main
                cell.font = header_font
            elif is_top_header or is_left_header:
                cell.fill = fill_side
                cell.font = header_font
            else:
                if body_fill:
                    cell.fill = body_fill


def _apply_number_format(ws: Worksheet, spec: StyleSpec) -> None:
    if spec.number_decimals is None:
        return

    decimals = int(spec.number_decimals)
    fmt = "0" if decimals <= 0 else "0." + ("0" * decimals)

    max_row = ws.max_row or 1
    max_col = ws.max_column or 1

    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            # Не форматировать заголовки
            if r <= spec.header_rows or c <= spec.header_cols:
                continue

            v = cell.value
            if v is None:
                continue

            # Формулы: опционально
            if isinstance(v, str) and v.startswith("="):
                if not spec.number_apply_to_formulas:
                    continue
                cell.number_format = fmt
                continue

            if isinstance(v, (int, float)):
                cell.number_format = fmt


def _apply_borders(ws: Worksheet, spec: StyleSpec) -> None:
    if not spec.apply_borders:
        return
    if not spec.palette:
        # без палитры неясно какие цвета границ использовать
        return

    pal = spec.palette

    thin_data = Side(style="thin", color=pal.data_border)
    thin_header = Side(style="thin", color=pal.header_border)

    max_row = ws.max_row or 1
    max_col = ws.max_column or 1

    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            is_header = (r <= spec.header_rows) or (c <= spec.header_cols)

            side = thin_header if is_header else thin_data
            cell.border = Border(left=side, right=side, top=side, bottom=side)


def apply_style(ws: Worksheet, spec: StyleSpec, *, freeze_panes: str | None = None) -> None:
    """
    Применяет StyleSpec к worksheet.

    freeze_panes:
    - если задан явно, использует его
    - иначе рассчитывает из freeze_rows/freeze_cols
    """
    _apply_gridlines(ws, spec.hide_gridlines)
    _apply_freeze(ws, spec.freeze_rows, spec.freeze_cols, freeze_panes)
    _apply_font(ws, spec)
    _apply_palette(ws, spec)
    _apply_number_format(ws, spec)
    _apply_borders(ws, spec)
