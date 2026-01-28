"""
rar — работа с RAR поверх FileStore.

Зависимости:
- rarfile (опционально)
- системная утилита: unrar или bsdtar (часто требуется rarfile)

Важно:
- запись RAR намеренно не реализуется (слишком зависит от внешних утилит).
  Для записи используйте zip.
"""

from __future__ import annotations

from pathlib import Path

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes
from stratbox.base.utils.optional_deps import ensure_import


def list_files(rar_path: str, store: FileStore | None = None, *, auto_install: bool | None = None) -> list[str]:
    """Возвращает список файлов внутри RAR-архива."""
    ensure_import(
        "rarfile",
        "rarfile>=4.0",
        auto_install=auto_install,
        hint="Also ensure that 'unrar' or 'bsdtar' is available in the system.",
    )

    import tempfile
    import rarfile  # type: ignore

    data = read_bytes(rar_path, store=store)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "tmp.rar"
        tmp.write_bytes(data)
        with rarfile.RarFile(str(tmp)) as rf:
            return rf.namelist()


def extract_to_memory(
    rar_path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
) -> dict[str, bytes]:
    """Извлекает все файлы из RAR в память: {имя_в_архиве: bytes}."""
    ensure_import(
        "rarfile",
        "rarfile>=4.0",
        auto_install=auto_install,
        hint="Also ensure that 'unrar' or 'bsdtar' is available in the system.",
    )

    import tempfile
    import rarfile  # type: ignore

    data = read_bytes(rar_path, store=store)
    out: dict[str, bytes] = {}

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "tmp.rar"
        tmp.write_bytes(data)
        with rarfile.RarFile(str(tmp)) as rf:
            for name in rf.namelist():
                out[name] = rf.read(name)
    return out