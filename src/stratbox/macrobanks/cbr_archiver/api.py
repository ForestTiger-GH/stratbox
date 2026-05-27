"""
Публичный API домена cbr_archiver.

Сценарий:
- взять реестр исходных статистических файлов Банка России;
- скачать файлы через общий сетевой слой stratbox;
- не редактировать содержимое файлов;
- сохранить результат через FileStore как ZIP или как пачку файлов;
- вернуть краткий машинно-читаемый отчет выполнения.
"""

from __future__ import annotations

from typing import Iterable, Literal

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.cbr_archiver.downloader import download_sources
from stratbox.macrobanks.cbr_archiver.models import CbrArchiveSource, CbrArchiverRunResult
from stratbox.macrobanks.cbr_archiver.naming import ensure_unique_download_file_names
from stratbox.macrobanks.cbr_archiver.output import save_as_files, save_as_zip
from stratbox.macrobanks.cbr_archiver.registry import (
    DEFAULT_ARCHIVE_BASE_NAME,
    DEFAULT_CBR_ARCHIVE_SOURCES,
    DEFAULT_FOLDER_NAME,
    DEFAULT_HEADERS,
    DEFAULT_OUTPUT_BASE_DIR,
)

OutputMode = Literal["zip", "files"]


def _coerce_sources(
    sources: Iterable[CbrArchiveSource | str] | None,
) -> list[CbrArchiveSource]:
    """Приводит пользовательский список источников к CbrArchiveSource."""
    raw_sources = list(sources) if sources is not None else list(DEFAULT_CBR_ARCHIVE_SOURCES)
    out: list[CbrArchiveSource] = []
    for idx, item in enumerate(raw_sources, start=1):
        if isinstance(item, CbrArchiveSource):
            out.append(item)
        else:
            out.append(
                CbrArchiveSource(
                    url=str(item),
                    group="custom",
                    code=f"custom_{idx:03d}",
                    title=f"Custom CBR source {idx}",
                )
            )
    return out


def _filter_sources_by_group(
    sources: list[CbrArchiveSource],
    source_groups: Iterable[str] | None,
) -> list[CbrArchiveSource]:
    """Фильтрует источники по группам реестра."""
    if source_groups is None:
        return sources

    groups = {str(item).strip().lower() for item in source_groups if str(item).strip()}
    if not groups:
        return sources

    return [item for item in sources if item.group.lower() in groups]


def run_cbr_archiver(
    *,
    out_path: str = DEFAULT_OUTPUT_BASE_DIR,
    output_mode: OutputMode = "zip",
    sources: Iterable[CbrArchiveSource | str] | None = None,
    source_groups: Iterable[str] | None = None,
    archive_name: str | None = None,
    archive_base_name: str = DEFAULT_ARCHIVE_BASE_NAME,
    folder_name: str | None = DEFAULT_FOLDER_NAME,
    date_in_name: bool = False,
    replace_existing: bool = True,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
    try_case_variants: bool = True,
    continue_on_error: bool = True,
    show_progress: bool = True,
    filestore: FileStore | None = None,
) -> CbrArchiverRunResult:
    """
    Скачивает исходные статистические файлы Банка России и сохраняет их.

    Параметры:
    - out_path: базовая папка или полный путь к .zip в режиме output_mode='zip';
    - output_mode: 'zip' для одного архива или 'files' для папки файлов;
    - sources: свой список CbrArchiveSource или строк-URL; если None, используется реестр;
    - source_groups: опциональный фильтр по группам реестра;
    - archive_name: явное имя архива, если out_path не является .zip;
    - folder_name: подпапка для режима files; если None, out_path используется как итоговая папка;
    - replace_existing: при True существующие файлы перезаписываются;
    - plugin_only: передается в сетевой слой stratbox для корпоративных URL-шлюзов.
    """
    mode = str(output_mode).strip().lower()
    if mode not in ("zip", "files"):
        raise ValueError("output_mode must be 'zip' or 'files'")

    store = filestore or get_filestore()
    prepared_sources = _filter_sources_by_group(_coerce_sources(sources), source_groups)
    if not prepared_sources:
        raise ValueError("No CBR sources selected for download")

    downloaded, failed = download_sources(
        prepared_sources,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
        try_case_variants=try_case_variants,
        continue_on_error=continue_on_error,
        show_progress=show_progress,
    )

    downloaded = ensure_unique_download_file_names(downloaded)
    if not downloaded:
        details = "; ".join(f"{item.source.url} :: {item.error}" for item in failed[:5])
        raise RuntimeError(f"No CBR source files were downloaded. {details}")

    if mode == "zip":
        output_path, saved_paths, final_archive_name = save_as_zip(
            downloaded,
            out_path=out_path,
            store=store,
            archive_name=archive_name,
            archive_base_name=archive_base_name,
            date_in_name=date_in_name,
            replace_existing=replace_existing,
        )
        archive_name_out: str | None = final_archive_name
    else:
        output_path, saved_paths = save_as_files(
            downloaded,
            out_path=out_path,
            store=store,
            folder_name=folder_name,
            replace_existing=replace_existing,
        )
        archive_name_out = None

    downloaded_files = [item.file_name for item in downloaded]

    return CbrArchiverRunResult(
        output_path=output_path,
        output_mode=mode,
        saved_paths=saved_paths,
        downloaded_files=downloaded_files,
        failed_urls=[item.source.url for item in failed],
        total_sources=len(prepared_sources),
        downloaded_count=len(downloaded),
        failed_count=len(failed),
        archive_name=archive_name_out,
    )


__all__ = ["CbrArchiverRunResult", "CbrArchiveSource", "run_cbr_archiver"]
