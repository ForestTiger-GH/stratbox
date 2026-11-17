"""Apply the Excel style registry selected by the caller or the environment."""

from stratbox.core.runtime.providers import active_providers

from stratbox.core.runtime.dependencies import require_extra
from stratbox.core.rendering.excel.registry import BUILTIN_STYLES, ExcelStylesRegistry


def active_styles(registry: ExcelStylesRegistry | None = None) -> ExcelStylesRegistry:
    if registry is None:
        providers = active_providers()
        registry = (
            providers.excel_styles()
            if providers is not None and providers.excel_styles is not None
            else BUILTIN_STYLES
        )
    if not isinstance(registry, ExcelStylesRegistry):
        raise TypeError("Expected ExcelStylesRegistry from the selected provider")
    return registry


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
    # Style metadata remains available without the optional Excel engine.
    require_extra("openpyxl", "excel")
    from stratbox.core.rendering.excel.apply import apply_style

    apply_style(worksheet, registry.presets[resolved], freeze_panes=freeze_panes)
