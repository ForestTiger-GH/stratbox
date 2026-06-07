"""
download — скачивание и кэширование ежемесячных исходных файлов эскроу.
"""

from __future__ import annotations

from stratbox.base import ioapi as ia
from stratbox.base.filestore import FileStore
from stratbox.base.net import download_bytes
from stratbox.macrobanks.escrow.contracts import (
    EscrowSourceDownloadResult,
    EscrowSourceFailure,
    EscrowSourceLink,
)
from stratbox.macrobanks.escrow.sources import DEFAULT_HEADERS



def _join_path(parent: str, name: str) -> str:
    left = str(parent).replace("\\", "/").rstrip("/")
    right = str(name).replace("\\", "/").lstrip("/")
    if not left:
        return right
    return f"{left}/{right}"



def _looks_like_html(content: bytes, headers: dict[str, str] | None) -> bool:
    content_type = str((headers or {}).get("Content-Type") or (headers or {}).get("content-type") or "").lower()
    if "text/html" in content_type:
        return True
    head = (content[:256] or b"").strip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")



def try_download_escrow_source(
    source: EscrowSourceLink,
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
) -> tuple[EscrowSourceDownloadResult | None, EscrowSourceFailure | None]:
    """Скачивает или читает из кэша один исходный файл эскроу."""
    cache_path = _join_path(source_cache_dir, source.source_name) if source_cache_dir else None
    if cache_path and store.exists(cache_path) and not refresh:
        content = ia.bytes.read_bytes(cache_path, store=store)
        return (
            EscrowSourceDownloadResult(
                source_id=source.source_id,
                url=source.url,
                source_name=source.source_name,
                file_date_hint=source.file_date_hint,
                content=content,
                size_bytes=len(content),
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
        return (
            None,
            EscrowSourceFailure(
                source_id=source.source_id,
                url=source.url,
                source_name=source.source_name,
                error=result.error or "unknown download error",
                status_code=result.status_code,
                attempts_used=retries + 1,
                used_url=source.url,
                final_url=result.final_url,
            ),
        )

    if _looks_like_html(result.content, result.headers):
        return (
            None,
            EscrowSourceFailure(
                source_id=source.source_id,
                url=source.url,
                source_name=source.source_name,
                error="Downloaded content looks like HTML page, not Excel file",
                status_code=result.status_code,
                attempts_used=retries + 1,
                used_url=source.url,
                final_url=result.final_url,
            ),
        )

    if cache_path:
        ia.bytes.write_bytes(cache_path, result.content, store=store)

    return (
        EscrowSourceDownloadResult(
            source_id=source.source_id,
            url=source.url,
            source_name=source.source_name,
            file_date_hint=source.file_date_hint,
            content=result.content,
            size_bytes=len(result.content),
            used_url=source.url,
            final_url=result.final_url,
            cache_path=cache_path,
            from_cache=False,
        ),
        None,
    )


__all__ = ["try_download_escrow_source"]
