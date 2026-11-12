"""Apply explicitly selected Excel presentation styles."""

from .apply import apply_style
from .registry import BUILTIN_STYLES, ExcelStylesRegistry


def list_available_presets(*, registry: ExcelStylesRegistry = BUILTIN_STYLES) -> list[str]:
    return sorted(registry.presets)


def get_default_preset_name(*, registry: ExcelStylesRegistry = BUILTIN_STYLES) -> str:
    return registry.default_preset_name


def resolve_preset_name(name: str | None, *, registry: ExcelStylesRegistry = BUILTIN_STYLES) -> str | None:
    if name is None or not name.strip():
        return None
    key = name.strip().upper()
    return registry.default_preset_name if key == "DEFAULT" else key


def apply_preset(worksheet, name: str | None, *, freeze_panes: str | None = None,
                 registry: ExcelStylesRegistry = BUILTIN_STYLES) -> None:
    resolved = resolve_preset_name(name, registry=registry)
    if resolved is None:
        return
    if resolved not in registry.presets:
        raise ValueError(f"Unknown Excel style preset: {resolved!r}")
    apply_style(worksheet, registry.presets[resolved], freeze_panes=freeze_panes)
