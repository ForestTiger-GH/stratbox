"""
operations — канонические публичные операции домена escrow.
"""

from __future__ import annotations

from posixpath import basename as posix_basename
from urllib.parse import urlsplit

import pandas as pd

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.escrow.columns import get_output_indicator_specs
from stratbox.macrobanks.escrow.contracts import (
    EscrowExportResult,
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    EscrowPivotPack,
    EscrowSourceFailure,
    EscrowSourceLink,
    EscrowViewBuildRequest,
    EscrowWorkbookExportRequest,
)
from stratbox.macrobanks.escrow.download import try_download_escrow_source
from stratbox.macrobanks.escrow.export import save_workbook_xlsx, save_workbook_zip
from stratbox.macrobanks.escrow.parser import parse_escrow_excel_bytes
from stratbox.macrobanks.escrow.pivots import build_escrow_pivots
from stratbox.macrobanks.escrow.sources import (
    CBR_ESCROW_INDEX_URL,
    DEFAULT_HEADERS,
    discover_escrow_source_links,
)
from stratbox.macrobanks.escrow.workbook import build_escrow_workbook



def discover_escrow_sources(
    *,
    index_url: str = CBR_ESCROW_INDEX_URL,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
) -> tuple[EscrowSourceLink, ...]:
    """Публичная операция получения структурированного списка источников."""
    return discover_escrow_source_links(
        index_url=index_url,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers,
        plugin_only=plugin_only,
    )



def build_escrow_history(
    request: EscrowHistoryBuildRequest,
    *,
    filestore: FileStore | None = None,
) -> EscrowHistoryResult:
    """Строит нормализованный исторический набор данных по счетам эскроу."""
    normalized_policy = str(request.source_error_policy).strip().lower()
    if normalized_policy not in {"fail_fast", "collect_partial"}:
        raise ValueError(f"Unsupported source_error_policy: {request.source_error_policy}")

    store = filestore or get_filestore()
    source_links = tuple(
        discover_escrow_sources(
            index_url=request.index_url,
            timeout=request.timeout,
            retries=request.retries,
            backoff=request.backoff,
            min_bytes_ok=request.min_bytes_ok,
            headers=dict(request.headers) if request.headers is not None else None,
            plugin_only=request.plugin_only,
        )
    )
    if not source_links:
        raise RuntimeError("No escrow Excel links found on the source page")

    downloaded = []
    failures = []
    parsed_files = []

    iterator = source_links
    if request.show_progress:
        try:
            from tqdm.auto import tqdm

            iterator = tqdm(source_links, desc="Escrow sources", leave=False)
        except Exception:
            iterator = source_links

    for source in iterator:
        downloaded_result, failure = try_download_escrow_source(
            source,
            store=store,
            source_cache_dir=request.source_cache_dir,
            refresh=request.refresh,
            timeout=request.timeout,
            retries=request.retries,
            backoff=request.backoff,
            min_bytes_ok=request.min_bytes_ok,
            headers=dict(request.headers) if request.headers is not None else None,
            plugin_only=request.plugin_only,
        )
        if failure is not None:
            failures.append(failure)
            if normalized_policy == "fail_fast":
                raise RuntimeError(
                    f"Failed to download escrow source {failure.source_name}: {failure.error}"
                )
            continue

        assert downloaded_result is not None
        downloaded.append(downloaded_result)

        try:
            parsed = parse_escrow_excel_bytes(
                downloaded_result.content,
                source_name=downloaded_result.source_name,
            )
        except Exception as exc:
            parse_failure = EscrowSourceFailure(
                source_id=downloaded_result.source_id,
                url=downloaded_result.url,
                source_name=downloaded_result.source_name,
                error=f"{type(exc).__name__}: {exc}",
                status_code=None,
                attempts_used=request.retries + 1,
                used_url=downloaded_result.used_url,
                final_url=downloaded_result.final_url,
            )
            failures.append(parse_failure)
            if normalized_policy == "fail_fast":
                raise RuntimeError(
                    f"Failed to parse escrow source {parse_failure.source_name}: {parse_failure.error}"
                )
            continue

        parsed_files.append(parsed)

    parsed_files = sorted(parsed_files, key=lambda item: item.file_date or "")
    if not parsed_files:
        raise RuntimeError("No escrow source files were parsed successfully")

    long_df = pd.concat([item.df_long for item in parsed_files], ignore_index=True)
    dates = tuple(sorted([str(x) for x in long_df["Дата"].dropna().unique().tolist()]))
    present_indicators = set(str(x) for x in long_df["Показатель"].dropna().unique().tolist())
    indicators = tuple(
        spec.canonical_name for spec in get_output_indicator_specs() if spec.canonical_name in present_indicators
    )

    return EscrowHistoryResult(
        source_links=source_links,
        downloaded_sources=tuple(downloaded),
        failures=tuple(failures),
        parsed_files=tuple(parsed_files),
        df_long=long_df,
        dates=dates,
        indicators=indicators,
        rows_long=int(len(long_df)),
    )



def build_escrow_views(
    history_result: EscrowHistoryResult,
    request: EscrowViewBuildRequest | None = None,
) -> EscrowPivotPack:
    """Строит витринные таблицы по историческому набору данных эскроу."""
    req = request or EscrowViewBuildRequest()
    normalized_mode = str(req.regions_mode).strip().lower()
    if normalized_mode not in {"latest", "custom"}:
        raise ValueError(f"Unsupported regions_mode: {req.regions_mode}")
    pivots, indicator_specs, region_order, date_order = build_escrow_pivots(
        history_result.df_long,
        parsed_files=history_result.parsed_files,
        regions_mode=normalized_mode,
        custom_regions=req.custom_regions,
    )
    return EscrowPivotPack(
        pivots=pivots,
        indicator_specs=tuple(indicator_specs),
        region_order=tuple(region_order),
        date_order=tuple(date_order),
    )



def export_escrow_workbook(
    history_result: EscrowHistoryResult,
    export_request: EscrowWorkbookExportRequest,
    *,
    view_request: EscrowViewBuildRequest | None = None,
    filestore: FileStore | None = None,
) -> EscrowExportResult:
    """Экспортирует итоговый workbook по истории эскроу в xlsx или zip."""
    store = filestore or get_filestore()
    pivot_pack = build_escrow_views(history_result, request=view_request)
    workbook = build_escrow_workbook(
        pivot_pack.pivots,
        list(pivot_pack.indicator_specs),
        show_progress=export_request.show_progress,
    )

    if export_request.archive:
        path_name = posix_basename(urlsplit(str(export_request.out_path)).path or "")
        default_member_name = (path_name[:-4] if path_name.lower().endswith(".zip") else path_name) or "escrow_accounts"
        member_name = export_request.archive_member_name or f"{default_member_name}.xlsx"
        output_path = save_workbook_zip(
            export_request.out_path,
            workbook,
            archive_member_name=member_name,
            store=store,
        )
    else:
        output_path = save_workbook_xlsx(export_request.out_path, workbook, store=store)

    return EscrowExportResult(
        output_path=output_path,
        archive=export_request.archive,
        source_files=tuple(item.source_name for item in history_result.parsed_files),
        dates=history_result.dates,
        indicators=tuple(spec.canonical_name for spec in pivot_pack.indicator_specs),
        regions=pivot_pack.region_order,
        rows_long=history_result.rows_long,
        source_links_count=len(history_result.source_links),
        failure_count=len(history_result.failures),
    )



def run_escrow_export(
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
    source_error_policy: str = "fail_fast",
    filestore: FileStore | None = None,
) -> EscrowExportResult:
    """Удобный wrapper полного export-сценария по счетам эскроу."""
    history_request = EscrowHistoryBuildRequest(
        index_url=index_url,
        source_cache_dir=source_cache_dir,
        refresh=refresh,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
        show_progress=show_progress,
        source_error_policy=str(source_error_policy).strip().lower(),
    )
    history = build_escrow_history(history_request, filestore=filestore)
    view_request = EscrowViewBuildRequest(
        regions_mode=str(regions_mode).strip().lower(),
        custom_regions=tuple(custom_regions or ()),
    )
    export_request = EscrowWorkbookExportRequest(
        out_path=out_path,
        archive=archive,
        archive_member_name=archive_member_name,
        show_progress=show_progress,
    )
    return export_escrow_workbook(
        history,
        export_request,
        view_request=view_request,
        filestore=filestore,
    )


__all__ = [
    "discover_escrow_sources",
    "build_escrow_history",
    "build_escrow_views",
    "export_escrow_workbook",
    "run_escrow_export",
]
