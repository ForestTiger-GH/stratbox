"""
save — сохранение скачанных исходных файлов Банка России через FileStore.

Поддерживаются два режима сохранения:
- zip: один архив с исходными файлами;
- files: каталог с исходными файлами без упаковки.
"""

from __future__ import annotations

from stratbox.base import ioapi as ia
from stratbox.base.filestore import FileStore
from stratbox.macrobanks.cbr_file_collector.contracts import CbrCollectedFile, CbrDownloadedFileSource, SaveMode


def _normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").rstrip("/")


def _join_path(parent: str, name: str) -> str:
    left = str(parent).replace("\\", "/").rstrip("/")
    right = str(name).replace("\\", "/").lstrip("/")
    if not left:
        return right
    return f"{left}/{right}"


def _parent_dir(path: str) -> str:
    normalized = _normalize_path(path)
    if not normalized or "/" not in normalized:
        return "."
    parent = normalized.rsplit("/", 1)[0]
    return parent or "/"


def _ensure_parent_dir(path: str, *, store: FileStore) -> None:
    store.makedirs(_parent_dir(path))


def _build_collected_files(downloaded: list[CbrDownloadedFileSource]) -> tuple[CbrCollectedFile, ...]:
    return tuple(
        CbrCollectedFile(
            source_id=item.source_id,
            url=item.url,
            file_name=item.file_name,
            size_bytes=item.size_bytes,
            used_url=item.used_url,
            final_url=item.final_url,
        )
        for item in downloaded
    )


def save_downloaded_sources(
    downloaded: list[CbrDownloadedFileSource],
    *,
    target_path: str,
    save_mode: SaveMode,
    store: FileStore,
    overwrite: bool,
) -> tuple[str, tuple[str, ...], tuple[CbrCollectedFile, ...]]:
    if save_mode == "zip":
        final_path = str(target_path).strip()
        if not final_path.lower().endswith(".zip"):
            raise ValueError("save_mode='zip' requires target_path that ends with .zip")
        if store.exists(final_path) and store.is_dir(final_path):
            raise IsADirectoryError(f"ZIP target path points to a directory: {final_path}")
        if store.exists(final_path) and not overwrite:
            raise FileExistsError(
                f"Target ZIP already exists: {final_path}. Pass overwrite=True to replace it."
            )
        _ensure_parent_dir(final_path, store=store)
        payload = {item.file_name: item.content for item in downloaded}
        ia.zip.write_zip_from_memory(final_path, payload, store=store)
        return final_path, (final_path,), _build_collected_files(downloaded)

    final_dir = str(target_path).strip()
    if final_dir.lower().endswith(".zip"):
        raise ValueError("save_mode='files' requires target_path that points to a directory")
    if store.exists(final_dir) and store.is_file(final_dir):
        raise NotADirectoryError(f"Files target path points to a file: {final_dir}")

    if not overwrite:
        conflicting = [
            item.file_name for item in downloaded if store.exists(_join_path(final_dir, item.file_name))
        ]
        if conflicting:
            raise FileExistsError(
                "Target directory already contains files that would be overwritten: "
                + ", ".join(conflicting)
            )

    store.makedirs(final_dir)
    saved_paths: list[str] = []
    for item in downloaded:
        final_path = _join_path(final_dir, item.file_name)
        ia.bytes.write_bytes(final_path, item.content, store=store)
        saved_paths.append(final_path)

    return final_dir, tuple(saved_paths), _build_collected_files(downloaded)


__all__ = ["save_downloaded_sources"]
