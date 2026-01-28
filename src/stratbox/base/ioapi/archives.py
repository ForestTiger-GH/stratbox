"""
archives — работа с zip-архивами поверх FileStore.

Минимальный набор:
- list_files(zip_path)
- extract_to_memory(zip_path) -> dict[name, bytes]
- write_zip_from_memory(zip_path, files: dict[name, bytes])
"""

from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def list_files(zip_path: str, store: FileStore | None = None) -> list[str]:
    data = read_bytes(zip_path, store=store)
    with ZipFile(BytesIO(data), "r") as zf:
        return zf.namelist()


def extract_to_memory(zip_path: str, store: FileStore | None = None) -> dict[str, bytes]:
    data = read_bytes(zip_path, store=store)
    out: dict[str, bytes] = {}
    with ZipFile(BytesIO(data), "r") as zf:
        for name in zf.namelist():
            out[name] = zf.read(name)
    return out


def write_zip_from_memory(zip_path: str, files: dict[str, bytes], store: FileStore | None = None) -> None:
    bio = BytesIO()
    with ZipFile(bio, "w", compression=ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    write_bytes(zip_path, bio.getvalue(), store=store)


# -------------------------
# RAR (опционально)
# -------------------------

def list_files_rar(rar_path: str, store: FileStore | None = None) -> list[str]:
    """Возвращает список файлов внутри RAR-архива. Требует rarfile + unrar/bsdtar."""
    try:
        import rarfile  # type: ignore
    except Exception as e:
        raise ImportError(
            "RAR support requires optional dependency 'rarfile'. Install: pip install rarfile. "
            "Also ensure that 'unrar' or 'bsdtar' is available in the system."
        ) from e

    import tempfile
    from pathlib import Path

    data = read_bytes(rar_path, store=store)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "tmp.rar"
        tmp.write_bytes(data)
        with rarfile.RarFile(str(tmp)) as rf:
            return rf.namelist()


def extract_to_memory_rar(rar_path: str, store: FileStore | None = None) -> dict[str, bytes]:
    """
    Извлекает все файлы из RAR в память: {имя_в_архиве: bytes}.
    Требует rarfile + unrar/bsdtar.
    """
    try:
        import rarfile  # type: ignore
    except Exception as e:
        raise ImportError(
            "RAR support requires optional dependency 'rarfile'. Install: pip install rarfile. "
            "Also ensure that 'unrar' or 'bsdtar' is available in the system."
        ) from e

    import tempfile
    from pathlib import Path

    data = read_bytes(rar_path, store=store)
    out: dict[str, bytes] = {}

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "tmp.rar"
        tmp.write_bytes(data)
        with rarfile.RarFile(str(tmp)) as rf:
            for name in rf.namelist():
                out[name] = rf.read(name)
    return out
