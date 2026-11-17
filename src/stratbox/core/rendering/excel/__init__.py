"""Built-in Excel presets and explicit style registry contracts."""

from stratbox.core.rendering.excel.api import apply_preset, get_default_preset_name, list_available_presets, resolve_preset_name
from stratbox.core.rendering.excel.models import BlockStyle, FontTheme, StyleSpec
from stratbox.core.rendering.excel.registry import BUILTIN_STYLES, ExcelStylesRegistry
