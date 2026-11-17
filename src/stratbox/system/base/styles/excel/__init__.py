"""Built-in Excel presets and explicit style registry contracts."""

from .main import apply_preset, get_default_preset_name, list_available_presets, resolve_preset_name
from .models import BlockStyle, FontTheme, StyleSpec
from .registry import BUILTIN_STYLES, ExcelStylesRegistry
