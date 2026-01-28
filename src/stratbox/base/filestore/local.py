"""
LocalFileStore — реализация FileStore для локальной файловой системы.

Используется вне контура, когда stratbox-plugin не установлен.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from stratbox.base.filestore.base import FileStore


class LocalFileStore(FileStore):
    """Локальная реализация FileStore."""

    def __init__(self, root: str | None = None):
        self._root = Path(root).expanduser().resolve() if root else None

    def _abs(self, path: str) -> Path:
        p = Path(path)
        if self._root and not p.is_absolute():
            p = self._root / p
        return p

    def open_read(self, path: str) -> BinaryIO:
        return self._abs(path).open("rb")

    def open_write(self, path: str) -> BinaryIO:
        p = self._abs(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.open("wb")

    def exists(self, path: str) -> bool:
        return self._abs(path).exists()

    def listdir(self, path: str) -> list[str]:
        p = self._abs(path)
        if not p.exists():
            return []
        return [x.name for x in p.iterdir()]

    def makedirs(self, path: str) -> None:
        self._abs(path).mkdir(parents=True, exist_ok=True)