"""
builtin-пресеты Excel-стилей (база из основного репозитория).

Комментарии — на русском (внешне, от третьего лица).
"""

from __future__ import annotations

from typing import Dict

from .models import FontTheme, StyleSpec, BlockStyle


FONT_THEMES: Dict[str, FontTheme] = {
    "ARIAL_10": FontTheme(name="Arial", size=10),
    "CALIBRI_11": FontTheme(name="Calibri", size=11),
}

# Базовые блоки (это просто удобные заготовки)
BLOCK_HEADER_GREEN = BlockStyle(
    fill="FF0B6B3A",
    font_color="FFFFFFFF",
    bold=True,
    border_color="FF2F2F2F",
    align_h="center",
    align_v="center",
    wrap_text=True,
)

BLOCK_VALUES_DEFAULT = BlockStyle(
    # По умолчанию ничего не задаётся => таблица может быть вообще без форматирования.
    # Но границы часто полезны, поэтому можно оставить border_color, если нравится.
    border_color="FFBFBFBF",
    align_h="general",
    align_v="center",
)

# Пресеты
PRESETS: Dict[str, StyleSpec] = {
    "MACROBANKS_GREEN": StyleSpec(
        hide_gridlines=True,
        freeze_rows=1,
        freeze_cols=2,

        header_rows=1,
        first_cols=0,  # ВАЖНО: первые столбцы по умолчанию = значения

        font_theme=FONT_THEMES["ARIAL_10"],

        number_decimals=0,
        number_apply_to_formulas=True,

        # "по умолчанию всё равно values"
        values_block=BLOCK_VALUES_DEFAULT,

        # отдельно оформляем заголовки
        header_block=BLOCK_HEADER_GREEN,

        # corner по умолчанию = header (можно явно задать при желании)
        corner_block=None,

        # first_cols по умолчанию не оформляем (они как values)
        first_cols_block=None,
    ),
}

# Дефолтный пресет core (если плагина нет).
DEFAULT_PRESET_NAME = "MACROBANKS_GREEN"
