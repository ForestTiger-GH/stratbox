"""
bytes — базовые операции поверх FileStore.

Это "универсальная база": Excel/XML/Zip и любые кастомные экспортеры.
"""

from __future__ import annotations

from typing import BinaryIO

from stratbox.base.filestore.base import FileStore
from stratbox.base.runtime import get_filestore


def open_read(path: str, store: FileStore | None = None) -> BinaryIO:
    store = store or get_filestore()
    return store.open_read(path)


def open_write(path: str, store: FileStore | None = None) -> BinaryIO:
    store = store or get_filestore()
    return store.open_write(path)


def read_bytes(path: str, store: FileStore | None = None) -> bytes:
    store = store or get_filestore()
    return store.read_bytes(path)


def write_bytes(path: str, data: bytes, store: FileStore | None = None) -> None:
    store = store or get_filestore()
    store.write_bytes(path, data)