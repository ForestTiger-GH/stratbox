"""
Подключение корпоративных Excel-пресетов через плагин.

Схема:
- StratBox содержит базу builtin-пресетов.
- Если установлен stratbox-plugin, он может вернуть дополнительные пресеты.
- Плагин может указать default preset (например: RSHB GREEN).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .models import FontTheme, ColorPalette, StyleSpec


@dataclass(frozen=True)
class ExcelStylesAddon:
    """
    Набор пресетов/палитр/шрифтов, которые добавляет плагин.

    Важно:
    - presets добавляются/переопределяются по ключу (имена пресетов должны быть уникальны)
    - default_preset_name задаёт дефолт при установленном плагине
    """
    presets: Optional[Dict[str, StyleSpec]] = None
    palettes: Optional[Dict[str, ColorPalette]] = None
    fonts: Optional[Dict[str, FontTheme]] = None
    default_preset_name: Optional[str] = None


def load_addons_from_plugins() -> list[ExcelStylesAddon]:
    """
    Загружает аддоны через entry_points.

    Поддерживается несколько провайдеров (на будущее),
    сейчас обычно будет один: stratbox-plugin.
    """
    addons: list[ExcelStylesAddon] = []

    try:
        from importlib.metadata import entry_points

        eps = entry_points().select(group="stratbox.styles.excel", name="presets")
        for ep in eps:
            factory = ep.load()
            obj = factory()

            if isinstance(obj, ExcelStylesAddon):
                addons.append(obj)
            elif isinstance(obj, dict):
                addons.append(ExcelStylesAddon(**obj))
            # иначе — игнорировать молча (не засорять вывод пользователю)
    except Exception:
        return []

    return addons
