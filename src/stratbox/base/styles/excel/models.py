"""
Модели Excel-стилей.

Комментарии — на русском (внешне, от третьего лица).
Print/логи (если появятся) — на английском.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal


AlignH = Literal["left", "center", "right", "general"]
AlignV = Literal["top", "center", "bottom"]


@dataclass(frozen=True)
class FontTheme:
    """Тема шрифта (общая для всей таблицы)."""
    name: str
    size: int


@dataclass(frozen=True)
class BlockStyle:
    """
    Опциональное форматирование блока таблицы.

    Принцип:
    - None => параметр не применяется (не трогает)
    - значение => применяется
    """
    fill: Optional[str] = None  # ARGB, например "FF0B6B3A"
    font_color: Optional[str] = None  # ARGB
    bold: Optional[bool] = None

    border_color: Optional[str] = None  # ARGB, thin border
    align_h: Optional[AlignH] = None
    align_v: Optional[AlignV] = None
    wrap_text: Optional[bool] = None


@dataclass
class StyleSpec:
    """
    Спецификация стиля Excel-таблицы.

    Ключевая идея:
    - values_block задаёт "базу" (по умолчанию это пустой стиль)
    - header/first_cols/corner — накладываются поверх базы (только заданные поля)
    """
    # базовое
    hide_gridlines: bool = True

    # freeze: закрепление строк/столбцов (НЕ связано с форматированием)
    freeze_rows: int = 1
    freeze_cols: int = 2

    # параметры разметки блоков
    header_rows: int = 1          # сколько верхних строк считать "заголовком"
    first_cols: int = 0           # сколько первых столбцов считать "первой зоной" (НЕ заголовок)

    # шрифт общий
    font_theme: Optional[FontTheme] = None

    # числовой формат (опционально)
    number_decimals: Optional[int] = 0
    number_apply_to_formulas: bool = True

    # блоки (все опциональны)
    values_block: Optional[BlockStyle] = None
    header_block: Optional[BlockStyle] = None
    first_cols_block: Optional[BlockStyle] = None
    corner_block: Optional[BlockStyle] = None
