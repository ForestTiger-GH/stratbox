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
import re

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

    def __init__(self, message: str, *, capability_missing: bool = False, code: str | None = None):
        super().__init__(message)
        if code is not None and not re.fullmatch(r"[a-z][a-z0-9_.-]{0,95}", code):
            raise ValueError("Invalid storage diagnostic code")
        self.capability_missing = capability_missing
        self.code = code or ("provider.capability_missing" if capability_missing else "effect.rejected")


DIRECTORY_GUARD_NAME = ".stratbox-directory.lock"
