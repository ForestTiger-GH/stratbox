"""Apply the Excel style registry selected by the caller or the environment."""

from stratbox.base.runtime import active_providers

from .apply import apply_style
from .registry import BUILTIN_STYLES, ExcelStylesRegistry


def active_styles(registry: ExcelStylesRegistry | None = None) -> ExcelStylesRegistry:
    if registry is not None:
        return registry
    providers = active_providers()
    if providers is not None and providers.excel_styles is not None:
        return providers.excel_styles()
    return BUILTIN_STYLES


def list_available_presets(*, registry: ExcelStylesRegistry | None = None) -> list[str]:
    return sorted(active_styles(registry).presets)


def get_default_preset_name(*, registry: ExcelStylesRegistry | None = None) -> str:
    return active_styles(registry).default_preset_name


def resolve_preset_name(name: str | None, *, registry: ExcelStylesRegistry | None = None) -> str | None:
    if name is None or not name.strip():
        return None
    key = name.strip().upper()
    return get_default_preset_name(registry=registry) if key == "DEFAULT" else key


def apply_preset(worksheet, name: str | None, *, freeze_panes: str | None = None,
                 registry: ExcelStylesRegistry | None = None) -> None:
    if name is None or not name.strip():
        return
    registry = active_styles(registry)
    resolved = resolve_preset_name(name, registry=registry)
    if resolved not in registry.presets:
        raise ValueError(f"Unknown Excel style preset: {resolved!r}")
    apply_style(worksheet, registry.presets[resolved], freeze_panes=freeze_panes)
