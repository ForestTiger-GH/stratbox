"""
Публичный API домена счетов эскроу.

Сценарий:
- получить список ежемесячных Excel-файлов на странице ЦБ;
- скачать файлы через общий сетевой слой stratbox;
- при необходимости сохранить исходники через FileStore;
- распарсить файлы в семантически правильный "длинный" поток данных;
- собрать сводные таблицы и итоговую Excel-книгу;
- сохранить .xlsx или .zip через FileStore.
"""

from __future__ import annotations

from dataclasses import dataclass
from posixpath import basename as posix_basename
from urllib.parse import urlsplit

import pandas as pd

from stratbox.base import ioapi as ia
from stratbox.base.filestore import FileStore
from stratbox.base.net import download_bytes
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.escrow.output import save_workbook_xlsx, save_workbook_zip
from stratbox.macrobanks.escrow.parser import ParsedEscrowFile, parse_escrow_excel_bytes
from stratbox.macrobanks.escrow.pivots import build_escrow_pivots
from stratbox.macrobanks.escrow.sources import CBR_ESCROW_INDEX_URL, DEFAULT_HEADERS, fetch_escrow_excel_links
from stratbox.macrobanks.escrow.workbook import build_escrow_workbook


@dataclass(frozen=True)
class EscrowRunResult:
    """Краткий результат выполнения конвейера по счетам эскроу."""

    output_path: str
    archive: bool
    source_files: list[str]
    dates: list[str]
    indicators: list[str]
    regions: list[str]
    rows_long: int



def _join_path(parent: str, name: str) -> str:
    """Склеивает пути в POSIX-стиле без привязки к локальной ОС."""
    left = str(parent).replace("\\", "/").rstrip("/")
    right = str(name).replace("\\", "/").lstrip("/")
    if not left:
        return right
    return f"{left}/{right}"



def _name_from_url(url: str) -> str:
    """Извлекает имя файла из URL страницы/ресурса."""
    path = urlsplit(str(url)).path or ""
    name = posix_basename(path)
    return name or "escrow_source.xlsx"



def _load_source_bytes(
    url: str,
    *,
    store: FileStore,
    source_cache_dir: str | None,
    refresh: bool,
    timeout: int,
    retries: int,
    backoff: float,
    min_bytes_ok: int,
    headers: dict[str, str] | None,
    plugin_only: bool,
) -> tuple[bytes, str]:
    """
    Возвращает bytes исходного файла и его условное имя.

    Если указан source_cache_dir, файл читается/пишется через FileStore.
    """
    source_name = _name_from_url(url)

    if source_cache_dir:
        cache_path = _join_path(source_cache_dir, source_name)
        if store.exists(cache_path) and not refresh:
            return ia.bytes.read_bytes(cache_path, store=store), source_name
    else:
        cache_path = None

    download = download_bytes(
        url,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
    )
    if not download.ok or not download.content:
        raise RuntimeError(f"Failed to download escrow source file: {url} :: {download.error}")

    content = download.content
    if cache_path:
        ia.bytes.write_bytes(cache_path, content, store=store)

    return content, source_name



def run_escrow_to_xlsx(
    *,
    out_path: str,
    archive: bool = False,
    archive_member_name: str | None = None,
    source_cache_dir: str | None = None,
    refresh: bool = False,
    index_url: str = CBR_ESCROW_INDEX_URL,
    regions_mode: str = "latest",
    custom_regions: list[str] | tuple[str, ...] | None = None,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
    show_progress: bool = True,
    filestore: FileStore | None = None,
) -> EscrowRunResult:
    """
    Запускает полный конвейер обработки счетов эскроу и сохраняет итоговый файл.

    Параметры:
    - out_path: путь к итоговому .xlsx или .zip (через активный FileStore);
    - archive: если True, сохраняется zip-архив, внутри которого лежит xlsx;
    - source_cache_dir: путь для сохранения исходных месячных Excel-файлов;
    - refresh: при True исходные файлы скачиваются заново даже при наличии кэша;
    - regions_mode: 'latest' или 'custom'; режим 'registry' зарезервирован на будущее.
    """
    store = filestore or get_filestore()

    links = fetch_escrow_excel_links(
        index_url=index_url,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
    )
    if not links:
        raise RuntimeError("No escrow Excel links found on the source page")

    parsed_files: list[ParsedEscrowFile] = []
    source_files: list[str] = []

    iterator = links
    if show_progress:
        try:
            from tqdm.auto import tqdm

            iterator = tqdm(links, desc="Escrow sources", leave=False)
        except Exception:
            iterator = links

    for url in iterator:
        file_bytes, source_name = _load_source_bytes(
            url,
            store=store,
            source_cache_dir=source_cache_dir,
            refresh=refresh,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            min_bytes_ok=min_bytes_ok,
            headers=headers,
            plugin_only=plugin_only,
        )
        parsed = parse_escrow_excel_bytes(file_bytes, source_name=source_name)
        parsed_files.append(parsed)
        source_files.append(source_name)

    parsed_files = sorted(parsed_files, key=lambda item: item.file_date or "")

    if not parsed_files:
        raise RuntimeError("No escrow source files were parsed successfully")

    long_df = pd.concat([item.df_long for item in parsed_files], ignore_index=True)
    pivots, indicator_specs, region_order, date_order = build_escrow_pivots(
        long_df,
        parsed_files=parsed_files,
        regions_mode=regions_mode,
        custom_regions=custom_regions,
    )

    workbook = build_escrow_workbook(
        pivots,
        indicator_specs,
        show_progress=show_progress,
    )

    if archive:
        member_name = archive_member_name or _name_from_url(out_path).replace(".zip", ".xlsx")
        final_output_path = save_workbook_zip(
            out_path,
            workbook,
            archive_member_name=member_name,
            store=store,
        )
    else:
        final_output_path = save_workbook_xlsx(out_path, workbook, store=store)

    return EscrowRunResult(
        output_path=final_output_path,
        archive=archive,
        source_files=source_files,
        dates=date_order,
        indicators=[spec.canonical_name for spec in indicator_specs],
        regions=region_order,
        rows_long=int(len(long_df)),
    )


__all__ = ["EscrowRunResult", "run_escrow_to_xlsx"]
