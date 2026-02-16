"""
builtin-пресеты Excel-стилей (база из основного репозитория).

Комментарии — на русском (внешне, от третьего лица).
"""

from __future__ import annotations

from typing import Dict

from .models import FontTheme, ColorPalette, StyleSpec


FONT_THEMES: Dict[str, FontTheme] = {
    "ARIAL": FontTheme(name="Arial", size=10, header_bold=True),
    "CALIBRI": FontTheme(name="Calibri", size=11, header_bold=True),
}

PALETTES: Dict[str, ColorPalette] = {
    "GREEN": ColorPalette(
        name="GREEN",
        header_fill_main="FF0B6B3A",
        header_fill_side="FFF2F2F2",
        header_font_color="FFFFFFFF",
        data_border="FFBFBFBF",
        header_border="FF2F2F2F",
        data_fill=None,
    ),
    "BLUE": ColorPalette(
        name="BLUE",
        header_fill_main="FF1F4E79",
        header_fill_side="FFF2F2F2",
        header_font_color="FFFFFFFF",
        data_border="FFBFBFBF",
        header_border="FF2F2F2F",
        data_fill=None,
    ),
}

PRESETS: Dict[str, StyleSpec] = {
    "MACROBANKS_GREEN": StyleSpec(
        hide_gridlines=True,
        freeze_rows=1,
        freeze_cols=2,
        font_theme=FONT_THEMES["ARIAL"],
        header_rows=1,
        header_cols=2,
        number_decimals=0,
        number_apply_to_formulas=True,
        palette=PALETTES["GREEN"],
        apply_borders=True,
    ),
    "MACROBANKS_BLUE": StyleSpec(
        hide_gridlines=True,
        freeze_rows=1,
        freeze_cols=2,
        font_theme=FONT_THEMES["ARIAL"],
        header_rows=1,
        header_cols=2,
        number_decimals=0,
        number_apply_to_formulas=True,
        palette=PALETTES["BLUE"],
        apply_borders=True,
    ),
}

# Дефолтный пресет core (если плагина нет).
DEFAULT_PRESET_NAME = "MACROBANKS_GREEN"
