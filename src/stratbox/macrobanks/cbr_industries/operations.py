"""Публичные операции серии Банка России ``01_05_A_Debt_corp``."""

from __future__ import annotations

import pandas as pd

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpDownloadBatchResult,
    Cbr0105ADebtCorpDownloadedSource,
    Cbr0105ADebtCorpDownloadRequest,
    Cbr0105ADebtCorpSourceFailure,
    Cbr0105ADebtCorpSourceLink,
    Cbr0105ADebtCorpStreamBuildRequest,
    Cbr0105ADebtCorpStreamResult,
    ParsedCbr0105ADebtCorpFile,
)
from stratbox.macrobanks.cbr_industries.download import (
    try_download_cbr_0105a_debt_corp_source,
)
from stratbox.macrobanks.cbr_industries.parser import (
    optimize_cbr_0105a_debt_corp_stream_dtypes,
    parse_cbr_0105a_debt_corp_source,
)
from stratbox.macrobanks.cbr_industries.regions import (
    normalize_cbr_0105a_debt_corp_regions_to_latest,
)
from stratbox.macrobanks.cbr_industries.sources import (
    CBR_SORS_INDEX_URL,
    DEFAULT_HEADERS,
    discover_cbr_0105a_debt_corp_source_links,
)


def _normalize_error_policy(value: str) -> str:
    policy = str(value).strip().lower()
    if policy not in {"fail_fast", "collect_partial"}:
        raise ValueError(f"Unsupported source_error_policy: {value!r}")
    return policy


def _progress(items, *, enabled: bool, description: str):
    if not enabled:
        return items
    try:
        from tqdm.auto import tqdm

        return tqdm(items, desc=description, leave=False)
    except Exception:
        return items


def discover_cbr_0105a_debt_corp_sources(
    *,
    index_url: str = CBR_SORS_INDEX_URL,
    date_from: str | None = None,
    date_to: str | None = None,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
) -> tuple[Cbr0105ADebtCorpSourceLink, ...]:
    """Возвращает официальный каталог книг ``01_05_A_Debt_corp``."""
    return discover_cbr_0105a_debt_corp_source_links(
        index_url=index_url,
        date_from=date_from,
        date_to=date_to,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers,
        plugin_only=plugin_only,
    )


def download_cbr_0105a_debt_corp_sources(
    request: Cbr0105ADebtCorpDownloadRequest,
    *,
    filestore: FileStore | None = None,
) -> Cbr0105ADebtCorpDownloadBatchResult:
    """Обнаруживает и скачивает исходные книги, не выполняя парсинг."""
    policy = _normalize_error_policy(request.source_error_policy)
    store = filestore or get_filestore()
    source_links = discover_cbr_0105a_debt_corp_sources(
        index_url=request.index_url,
        date_from=request.date_from,
        date_to=request.date_to,
        timeout=request.timeout,
        retries=request.retries,
        backoff=request.backoff,
        min_bytes_ok=request.min_bytes_ok,
        headers=dict(request.headers) if request.headers is not None else None,
        plugin_only=request.plugin_only,
    )
    if not source_links:
        raise RuntimeError("No 01_05_A_Debt_corp sources found for the selected period")

    downloaded = []
    failures = []
    for source in _progress(
        source_links,
        enabled=request.show_progress,
        description="CBR 01_05_A_Debt_corp download",
    ):
        result, failure = try_download_cbr_0105a_debt_corp_source(
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
            if policy == "fail_fast":
                raise RuntimeError(
                    f"Failed to download {failure.source_name}: {failure.error}"
                )
            continue
        assert result is not None
        downloaded.append(result)

    return Cbr0105ADebtCorpDownloadBatchResult(
        source_links=source_links,
        downloaded_sources=tuple(downloaded),
        failures=tuple(failures),
    )


def parse_cbr_0105a_debt_corp_downloaded_source(
    source: Cbr0105ADebtCorpDownloadedSource,
) -> ParsedCbr0105ADebtCorpFile:
    """Публичная операция разбора одной ранее скачанной книги."""
    return parse_cbr_0105a_debt_corp_source(source)


def build_cbr_0105a_debt_corp_stream(
    request: Cbr0105ADebtCorpStreamBuildRequest,
    *,
    filestore: FileStore | None = None,
) -> Cbr0105ADebtCorpStreamResult:
    """Скачивает, разбирает и объединяет книги в нормализованный поток."""
    policy = _normalize_error_policy(request.source_error_policy)
    download_result = download_cbr_0105a_debt_corp_sources(
        Cbr0105ADebtCorpDownloadRequest(
            index_url=request.index_url,
            date_from=request.date_from,
            date_to=request.date_to,
            source_cache_dir=request.source_cache_dir,
            refresh=request.refresh,
            timeout=request.timeout,
            retries=request.retries,
            backoff=request.backoff,
            min_bytes_ok=request.min_bytes_ok,
            headers=request.headers or DEFAULT_HEADERS,
            plugin_only=request.plugin_only,
            show_progress=request.show_progress,
            source_error_policy=request.source_error_policy,
        ),
        filestore=filestore,
    )

    failures = list(download_result.failures)
    parsed_files: list[ParsedCbr0105ADebtCorpFile] = []
    for source in _progress(
        download_result.downloaded_sources,
        enabled=request.show_progress,
        description="CBR 01_05_A_Debt_corp parse",
    ):
        try:
            parsed_files.append(parse_cbr_0105a_debt_corp_source(source))
        except Exception as exc:
            failure = Cbr0105ADebtCorpSourceFailure(
                stage="parse",
                source_id=source.source_id,
                url=source.url,
                source_name=source.source_name,
                report_date=source.report_date,
                error=f"{type(exc).__name__}: {exc}",
                status_code=None,
                attempts_used=1,
                used_url=source.used_url,
                final_url=source.final_url,
            )
            failures.append(failure)
            if policy == "fail_fast":
                raise RuntimeError(
                    f"Failed to parse {failure.source_name}: {failure.error}"
                ) from exc

    if not parsed_files:
        raise RuntimeError("No 01_05_A_Debt_corp workbooks were parsed successfully")

    normalized_files = normalize_cbr_0105a_debt_corp_regions_to_latest(parsed_files)
    stream = pd.concat([item.df_stream for item in normalized_files], ignore_index=True)
    stream = optimize_cbr_0105a_debt_corp_stream_dtypes(stream)
    stream = stream.sort_values(
        ["report_date", "sheet_order", "region_order", "industry_order"],
        kind="stable",
    ).reset_index(drop=True)
    dates = tuple(sorted(str(value) for value in stream["report_date"].dropna().unique()))
    latest_file = max(normalized_files, key=lambda item: item.report_date)

    return Cbr0105ADebtCorpStreamResult(
        source_links=download_result.source_links,
        downloaded_sources=download_result.downloaded_sources,
        failures=tuple(failures),
        parsed_files=normalized_files,
        validation_issues=tuple(
            issue for parsed in normalized_files for issue in parsed.validation_issues
        ),
        df_stream=stream,
        dates=dates,
        latest_report_date=latest_file.report_date,
        region_names=tuple(item.canonical_name for item in latest_file.regions),
        industry_codes=tuple(item.code for item in latest_file.industries),
        rows_stream=int(len(stream)),
    )


__all__ = [
    "build_cbr_0105a_debt_corp_stream",
    "discover_cbr_0105a_debt_corp_sources",
    "download_cbr_0105a_debt_corp_sources",
    "parse_cbr_0105a_debt_corp_downloaded_source",
]
