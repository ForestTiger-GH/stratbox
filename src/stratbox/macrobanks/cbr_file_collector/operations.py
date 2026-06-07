"""
operations — публичные операции домена загрузки исходных файлов Банка России.
"""

from __future__ import annotations

from typing import Iterable

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.cbr_file_collector.contracts import (
    CbrFileRegistryItem,
    CbrFileCollectRequest,
    CbrFileCollectResult,
)
from stratbox.macrobanks.cbr_file_collector.downloader import download_sources
from stratbox.macrobanks.cbr_file_collector.file_names import ensure_unique_download_file_names
from stratbox.macrobanks.cbr_file_collector.registry import DEFAULT_CBR_FILE_SOURCES
from stratbox.macrobanks.cbr_file_collector.save import save_downloaded_sources


def list_cbr_file_sources(*, registry: Iterable[CbrFileRegistryItem] | None = None) -> tuple[CbrFileRegistryItem, ...]:
    items = tuple(registry) if registry is not None else DEFAULT_CBR_FILE_SOURCES
    return tuple(items)


def collect_cbr_files(
    request: CbrFileCollectRequest,
    *,
    registry: Iterable[CbrFileRegistryItem] | None = None,
    filestore: FileStore | None = None,
) -> CbrFileCollectResult:
    target_path = str(request.target_path).strip()
    if not target_path:
        raise ValueError("target_path must not be empty")
    if request.save_mode not in {"zip", "files"}:
        raise ValueError("save_mode must be either 'zip' or 'files'")
    if request.retry_attempts < 1:
        raise ValueError("retry_attempts must be at least 1")
    if request.timeout_sec < 1:
        raise ValueError("timeout_sec must be at least 1")
    if request.min_bytes_ok < 1:
        raise ValueError("min_bytes_ok must be at least 1")
    if request.save_mode == "zip" and not target_path.lower().endswith(".zip"):
        raise ValueError("save_mode='zip' requires target_path that ends with .zip")
    if request.save_mode == "files" and target_path.lower().endswith(".zip"):
        raise ValueError("save_mode='files' requires target_path that points to a directory")

    store = filestore or get_filestore()
    sources = list_cbr_file_sources(registry=registry)

    downloaded, failures = download_sources(
        sources,
        timeout_sec=request.timeout_sec,
        retry_attempts=request.retry_attempts,
        retry_backoff_sec=request.retry_backoff_sec,
        min_bytes_ok=request.min_bytes_ok,
        headers=dict(request.headers) if request.headers is not None else None,
        plugin_only=request.plugin_only,
        try_case_variants=request.try_case_variants,
        continue_on_error=request.continue_on_error,
        show_progress=request.show_progress,
    )
    downloaded = ensure_unique_download_file_names(downloaded)

    saved_target_path = target_path
    saved_paths: tuple[str, ...] = tuple()
    collected_files = tuple()
    if downloaded:
        saved_target_path, saved_paths, collected_files = save_downloaded_sources(
            downloaded,
            target_path=target_path,
            save_mode=request.save_mode,
            store=store,
            overwrite=request.overwrite,
        )

    return CbrFileCollectResult(
        target_path=saved_target_path,
        save_mode=request.save_mode,
        saved_paths=saved_paths,
        collected_files=collected_files,
        failures=tuple(failures),
        requested_count=len(sources),
        success_count=len(collected_files),
        failure_count=len(failures),
    )


__all__ = ["collect_cbr_files", "list_cbr_file_sources"]
