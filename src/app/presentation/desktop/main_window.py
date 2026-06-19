from __future__ import annotations

# MainWindow moved to the scenario-first shell. This module is intentionally thin
# so stale legacy UI code cannot compete with the new target surface.
from app.presentation.desktop.shell.main_window import MainWindow

__all__ = ['MainWindow']
