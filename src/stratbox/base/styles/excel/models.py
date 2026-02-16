"""
Модели Excel-стилей.

Комментарии — на русском (внешне, от третьего лица).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FontTheme:
    """Тема шрифтов."""
    name: str
    size: int
    header_bold: bool = True


@dataclass(frozen=True)
class ColorPalette:
    """
    Палитра цветов (ARGB hex для openpyxl).

    ARGB: например "FF0B6B3A" (FF = полностью непрозрачный).
    """
    name: str

    # Заголовки
    header_fill_main: str
    header_fill_side: str
    header_font_color: str

    # Границы
    data_border: str
    header_border: str

    # Тело (опционально)
    data_fill: Optional[str] = None


@dataclass
class StyleSpec:
    """
    Полная спецификация стиля.

    Принцип:
    - если параметр None => фича не применяется (не трогает существующее)
    - если число/значение => применяется
    """
    # базовое
    hide_gridlines: bool = True

    # freeze: сколько закрепить строк/столбцов (0 => не закреплять)
    freeze_rows: int = 1
    freeze_cols: int = 2

    # шрифт
    font_theme: Optional[FontTheme] = None

    # заголовки (верхние строки / левые столбцы)
    header_rows: int = 1
    header_cols: int = 2

    # числовой формат:
    # decimals=None => не применять числовой формат
    # decimals=0/1/2/3 => применять
    number_decimals: Optional[int] = 0
    number_apply_to_formulas: bool = True

    # палитра
    palette: Optional[ColorPalette] = None

    # применять границы
    apply_borders: bool = True
