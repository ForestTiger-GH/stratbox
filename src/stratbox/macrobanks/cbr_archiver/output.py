"""
output — сохранение исходных файлов Банка России через FileStore stratbox.

Поддерживаются два режима:
- zip: один архив с исходными файлами;
- files: папка с исходными файлами без упаковки.
"""

from __future__ import annotations

import datetime as dt

from stratbox.base import ioapi as ia
from stratbox.base.filestore import FileStore
from stratbox.macrobanks.cbr_archiver.models import CbrDownloadedFile
from stratbox.macrobanks.cbr_archiver.registry import (
    DEFAULT_ARCHIVE_BASE_NAME,
    DEFAULT_FOLDER_NAME,
)


def join_path(parent: str, name: str) -> str:
    """Склеивает пути в POSIX-стиле без привязки к локальной ОС."""
    left = str(parent).replace("\\", "/").rstrip("/")
    right = str(name).replace("\\", "/").lstrip("/")
    if not left:
        return right
    return f"{left}/{right}"


def normalize_zip_name(name: str) -> str:
    """Гарантирует расширение .zip у имени архива."""
    text = str(name).strip()
    if not text.lower().endswith(".zip"):
        return f"{text}.zip"
    return text


def build_archive_name(
    *,
    archive_base_name: str = DEFAULT_ARCHIVE_BASE_NAME,
    date_in_name: bool = False,
    run_date: dt.date | None = None,
) -> str:
    """Строит имя ZIP-архива с опциональной датой."""
    base = str(archive_base_name).strip() or DEFAULT_ARCHIVE_BASE_NAME
    if base.lower().endswith(".zip"):
        base = base[:-4]

    if date_in_name:
        day = run_date or dt.date.today()
        base = f"{base} {day:%Y-%m-%d}"

    return normalize_zip_name(base)


def resolve_zip_output_path(
    out_path: str,
    *,
    archive_name: str | None = None,
    archive_base_name: str = DEFAULT_ARCHIVE_BASE_NAME,
    date_in_name: bool = False,
    run_date: dt.date | None = None,
) -> str:
    """Определяет итоговый путь ZIP-архива."""
    target = str(out_path).strip()
    if target.lower().endswith(".zip"):
        return target

    name = archive_name or build_archive_name(
        archive_base_name=archive_base_name,
        date_in_name=date_in_name,
        run_date=run_date,
    )
    return join_path(target, normalize_zip_name(name))


def resolve_files_output_path(
    out_path: str,
    *,
    folder_name: str | None = DEFAULT_FOLDER_NAME,
) -> str:
    """Определяет итоговую папку для режима files."""
    target = str(out_path).strip()
    if target.lower().endswith(".zip"):
        raise ValueError("output_mode='files' requires a directory path, not a .zip path")
    if folder_name is None:
        return target
    return join_path(target, folder_name)


def _ensure_can_write(path: str, *, store: FileStore, replace_existing: bool) -> None:
    """Проверяет возможность записи без нежелательной перезаписи."""
    if store.exists(path) and not replace_existing:
        raise FileExistsError(
            f"Output already exists: {path}. Pass replace_existing=True to overwrite it."
        )


def save_as_zip(
    files: list[CbrDownloadedFile],
    *,
    out_path: str,
    store: FileStore,
    archive_name: str | None = None,
    archive_base_name: str = DEFAULT_ARCHIVE_BASE_NAME,
    date_in_name: bool = False,
    replace_existing: bool = True,
) -> tuple[str, list[str], str]:
    """Сохраняет исходные файлы в один ZIP-архив через FileStore."""
    final_path = resolve_zip_output_path(
        out_path,
        archive_name=archive_name,
        archive_base_name=archive_base_name,
        date_in_name=date_in_name,
    )
    _ensure_can_write(final_path, store=store, replace_existing=replace_existing)

    payload = {item.file_name: item.content for item in files}
    ia.zip.write_zip_from_memory(final_path, payload, store=store)
    return final_path, [final_path], final_path.split("/")[-1]


def save_as_files(
    files: list[CbrDownloadedFile],
    *,
    out_path: str,
    store: FileStore,
    folder_name: str | None = DEFAULT_FOLDER_NAME,
    replace_existing: bool = True,
) -> tuple[str, list[str]]:
    """Сохраняет исходные файлы отдельной пачкой через FileStore."""
    final_dir = resolve_files_output_path(out_path, folder_name=folder_name)
    store.makedirs(final_dir)

    saved_paths: list[str] = []
    for item in files:
        final_path = join_path(final_dir, item.file_name)
        _ensure_can_write(final_path, store=store, replace_existing=replace_existing)
        ia.bytes.write_bytes(final_path, item.content, store=store)
        saved_paths.append(final_path)

    return final_dir, saved_paths


__all__ = [
    "build_archive_name",
    "join_path",
    "normalize_zip_name",
    "resolve_files_output_path",
    "resolve_zip_output_path",
    "save_as_files",
    "save_as_zip",
]
