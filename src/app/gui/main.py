"""Запуск GUI приложения."""

from __future__ import annotations

from app.bootstrap.app_bootstrap import run_gui_surface
from app.core.context import AppContext


def run_gui(context: AppContext) -> int:
    """Запускает desktop surface Strategy Box."""
    return run_gui_surface(context)
