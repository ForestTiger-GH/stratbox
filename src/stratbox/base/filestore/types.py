"""
types — типы для FileStore.

Назначение:
- дать единый переносимый тип метаданных файла/каталога
- не привязываться к конкретному backend (local/samba/и т.д.)

Принцип:
- поля опциональны: разные бэкенды могут отдавать разный объём метаданных
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileStat:
    """Метаданные файла/каталога.

    Поля намеренно опциональны.
    Разные реализации FileStore могут отдавать разные поля.
    """

    path: str
    is_file: bool
    is_dir: bool
    size: int | None = None
    mtime: float | None = None
    atime: float | None = None
    ctime: float | None = None
