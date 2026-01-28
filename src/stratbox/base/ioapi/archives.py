"""
archives — фасад над zip/rar поверх FileStore.

Сохранено для обратной совместимости:
- list_files()
- extract_to_memory()
- write_zip_from_memory()

Новые модули:
- zip.py
- rar.py
"""

from __future__ import annotations

from stratbox.base.filestore.base import FileStore


def _is_rar(path: str) -> bool:
    return path.strip().lower().endswith(".rar")


def list_files(path: str, store: FileStore | None = None, *, auto_install: bool | None = None) -> list[str]:
    if _is_rar(path):
        from stratbox.base.ioapi import rar

        return rar.list_files(path, store=store, auto_install=auto_install)

    from stratbox.base.ioapi import zip

    return zip.list_files(path, store=store)


def extract_to_memory(path: str, store: FileStore | None = None, *, auto_install: bool | None = None) -> dict[str, bytes]:
    if _is_rar(path):
        from stratbox.base.ioapi import rar

        return rar.extract_to_memory(path, store=store, auto_install=auto_install)

    from stratbox.base.ioapi import zip

    return zip.extract_to_memory(path, store=store)


def write_zip_from_memory(zip_path: str, files: dict[str, bytes], store: FileStore | None = None) -> None:
    from stratbox.base.ioapi import zip

    return zip.write_zip_from_memory(zip_path, files, store=store)