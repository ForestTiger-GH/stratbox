"""Скачивание и кэширование исходных XLSX ``01_05_A_Debt_corp``."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from stratbox.base import ioapi as ia
from stratbox.base.filestore import FileStore
from stratbox.base.net import download_bytes
from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpDownloadedSource,
    Cbr0105ADebtCorpSourceFailure,
    Cbr0105ADebtCorpSourceLink,
)
from stratbox.macrobanks.cbr_industries.sources import DEFAULT_HEADERS


def _join_path(parent: str, *children: str) -> str:
    result = str(parent).replace("\\", "/").rstrip("/")
    if str(parent).replace("\\", "/").startswith("/") and not result:
        result = "/"
    for child in children:
        right = str(child).replace("\\", "/").strip("/")
        if not right:
            continue
        if result == "/":
            result = f"/{right}"
        elif result:
            result = f"{result}/{right}"
        else:
            result = right
    return result


def _is_valid_xlsx(content: bytes, *, min_bytes_ok: int) -> bool:
    if len(content) < min_bytes_ok or not content.startswith(b"PK"):
        return False
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            return "xl/workbook.xml" in names and "[Content_Types].xml" in names
    except (BadZipFile, OSError):
        return False


def _cache_path(source: Cbr0105ADebtCorpSourceLink, source_cache_dir: str | None) -> str | None:
    if not source_cache_dir:
        return None
    return _join_path(source_cache_dir, source.report_date[:4], source.source_name)


def try_download_cbr_0105a_debt_corp_source(
    source: Cbr0105ADebtCorpSourceLink,
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
) -> tuple[Cbr0105ADebtCorpDownloadedSource | None, Cbr0105ADebtCorpSourceFailure | None]:
    """Скачивает одну книгу или читает ее из кэша."""
    cache_path = _cache_path(source, source_cache_dir)
    if cache_path and store.exists(cache_path) and not refresh:
        cached = ia.bytes.read_bytes(cache_path, store=store)
        if _is_valid_xlsx(cached, min_bytes_ok=min_bytes_ok):
            return (
                Cbr0105ADebtCorpDownloadedSource(
                    source_id=source.source_id,
                    url=source.url,
                    source_name=source.source_name,
                    report_date=source.report_date,
                    content=cached,
                    size_bytes=len(cached),
                    sha256=sha256(cached).hexdigest(),
                    used_url=source.url,
                    final_url=source.url,
                    cache_path=cache_path,
                    from_cache=True,
                ),
                None,
            )

    result = download_bytes(
        source.url,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
    )
    if not result.ok or not result.content:
        return None, Cbr0105ADebtCorpSourceFailure(
            stage="download",
            source_id=source.source_id,
            url=source.url,
            source_name=source.source_name,
            report_date=source.report_date,
            error=result.error or "unknown download error",
            status_code=result.status_code,
            attempts_used=retries + 1,
            used_url=source.url,
            final_url=result.final_url,
        )
    if not _is_valid_xlsx(result.content, min_bytes_ok=min_bytes_ok):
        return None, Cbr0105ADebtCorpSourceFailure(
            stage="download",
            source_id=source.source_id,
            url=source.url,
            source_name=source.source_name,
            report_date=source.report_date,
            error="Downloaded content is not a valid XLSX workbook",
            status_code=result.status_code,
            attempts_used=retries + 1,
            used_url=source.url,
            final_url=result.final_url,
        )

    if cache_path:
        ia.bytes.write_bytes(cache_path, result.content, store=store)

    return (
        Cbr0105ADebtCorpDownloadedSource(
            source_id=source.source_id,
            url=source.url,
            source_name=source.source_name,
            report_date=source.report_date,
            content=result.content,
            size_bytes=len(result.content),
            sha256=sha256(result.content).hexdigest(),
            used_url=source.url,
            final_url=result.final_url,
            cache_path=cache_path,
            from_cache=False,
        ),
        None,
    )


__all__ = ["try_download_cbr_0105a_debt_corp_source"]
