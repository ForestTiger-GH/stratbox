"""
main-API для Excel-стилей.

Здесь реализовано:
- дефолтный пресет (core или plugin)
- список доступных пресетов (core + plugin при наличии)
- валидация имени пресета
- применение пресета к worksheet
"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from .apply import apply_style
from .registry import get_registry, list_preset_names


_DEFAULT_ALIAS = "DEFAULT"


def list_available_presets() -> list[str]:
    """
    Возвращает список доступных пресетов.

    Если плагин подключён, в списке будут и корпоративные.
    """
    names, _ = list_preset_names()
    return names


def get_default_preset_name() -> str:
    """
    Возвращает дефолтный пресет:
    - если есть plugin default => он
    - иначе builtin default
    """
    reg = get_registry()
    return reg.default_preset_name


def resolve_preset_name(name: str | None) -> str | None:
    """
    Приводит имя пресета к нормализованному виду.

    Правила:
    - None => None (значит "не применять стили")
    - "DEFAULT" (любой регистр) => дефолт из реестра
    - иначе => нормализованное имя
    """
    if name is None:
        return None

    n = str(name).strip()
    if not n:
        return None

    n_up = n.upper()
    if n_up == _DEFAULT_ALIAS:
        return get_default_preset_name()

    return n_up


def _raise_unknown_preset(requested: str) -> None:
    names, plugin_connected = list_preset_names()
    scope = "core + plugin" if plugin_connected else "core"
    available = ", ".join(names) if names else "(no presets)"
    raise ValueError(
        f"Unknown style preset: '{requested}'. "
        f"Available presets ({scope}): {available}"
    )


def apply_preset(ws: Worksheet, preset_name: str | None, *, freeze_panes: str | None = None) -> None:
    """
    Применяет пресет по имени.

    preset_name:
    - None => ничего не делает
    - "DEFAULT" => применяет дефолт (core или plugin)
    - "RSHB GREEN" / "MACROBANKS_GREEN" => применяет конкретный
    """
    resolved = resolve_preset_name(preset_name)
    if resolved is None:
        return

    reg = get_registry()
    if resolved not in reg.presets:
        _raise_unknown_preset(resolved)

    spec = reg.presets[resolved]
    apply_style(ws, spec, freeze_panes=freeze_panes)
