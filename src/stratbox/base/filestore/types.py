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

from stratbox.data import ByteIdentity


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
    is_symlink: bool = False


@dataclass(frozen=True, slots=True)
class FileVersion:
    path: str
    revision: str
    identity: ByteIdentity


class MutationRejected(OSError):
    """The backend rejected a command before changing a target."""

    def __init__(self, message: str, *, capability_missing: bool = False):
        super().__init__(message)
        self.capability_missing = capability_missing


DIRECTORY_GUARD_NAME = ".stratbox-directory.lock"
