"""Совместимый re-export shell-level main window.

Фактическая реализация surface теперь живёт в ``app.shell.main_window``.
"""

from app.shell.main_window import MainWindow

__all__ = ["MainWindow"]
