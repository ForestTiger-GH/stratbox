from __future__ import annotations

import os
import subprocess
from pathlib import Path


class PlatformServices:
    def open_path(self, path: str) -> None:
        p = Path(path)
        target = p if p.is_dir() else p.parent
        target = target if target.exists() else p
        if os.name == 'nt':
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(['xdg-open', str(target)])

    def copy_text(self, value: str) -> None:
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(value)
