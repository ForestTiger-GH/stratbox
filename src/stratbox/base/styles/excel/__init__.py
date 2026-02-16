"""
stratbox.base.styles.excel

Пакет Excel-стилей: модели, builtin-пресеты, подключение оверлеев из плагина,
и публичное API через main.py.
"""

from .models import FontTheme, ColorPalette, StyleSpec  # noqa: F401
from .main import (  # noqa: F401
    list_available_presets,
    get_default_preset_name,
    resolve_preset_name,
    apply_preset,
)
