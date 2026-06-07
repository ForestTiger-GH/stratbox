"""Product-layer package for Strategy Box desktop surface.

This package intentionally keeps ``__init__`` lightweight so service commands and
AppDock preflight can import product registry / runner without pulling GUI-only
PySide modules.
"""

__all__: list[str] = []
