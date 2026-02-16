"""
Реестр Excel-стилей: builtin + (опционально) аддоны из плагина.

Здесь же формируется единый список доступных пресетов и дефолт.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .models import FontTheme, ColorPalette, StyleSpec
from .builtin import FONT_THEMES, PALETTES, PRESETS, DEFAULT_PRESET_NAME
from .plugin import load_addons_from_plugins


@dataclass
class ExcelStylesRegistry:
    fonts: Dict[str, FontTheme]
    palettes: Dict[str, ColorPalette]
    presets: Dict[str, StyleSpec]
    default_preset_name: str
    plugin_connected: bool


_REGISTRY: ExcelStylesRegistry | None = None


def _norm_key(name: str) -> str:
    return str(name).strip().upper()


def get_registry(force_reload: bool = False) -> ExcelStylesRegistry:
    """
    Возвращает единый реестр:
    - builtin (core)
    - + plugin-пакеты пресетов (если они доступны)
    """
    global _REGISTRY
    if _REGISTRY is not None and not force_reload:
        return _REGISTRY

    fonts = {_norm_key(k): v for k, v in FONT_THEMES.items()}
    palettes = {_norm_key(k): v for k, v in PALETTES.items()}
    presets = {_norm_key(k): v for k, v in PRESETS.items()}

    default_name = _norm_key(DEFAULT_PRESET_NAME)
    plugin_connected = False

    addons = load_addons_from_plugins()
    if addons:
        plugin_connected = True

    # Подмешивание аддонов (если несколько — применяются по порядку)
    for addon in addons:
        if addon.fonts:
            for k, v in addon.fonts.items():
                fonts[_norm_key(k)] = v

        if addon.palettes:
            for k, v in addon.palettes.items():
                palettes[_norm_key(k)] = v

        if addon.presets:
            for k, v in addon.presets.items():
                presets[_norm_key(k)] = v

        if addon.default_preset_name:
            default_name = _norm_key(addon.default_preset_name)

    _REGISTRY = ExcelStylesRegistry(
        fonts=fonts,
        palettes=palettes,
        presets=presets,
        default_preset_name=default_name,
        plugin_connected=plugin_connected,
    )
    return _REGISTRY


def list_preset_names() -> Tuple[list[str], bool]:
    """
    Возвращает:
    - список имён пресетов (отсортированный)
    - флаг подключенности плагина
    """
    reg = get_registry()
    names = sorted(reg.presets.keys())
    return names, reg.plugin_connected
