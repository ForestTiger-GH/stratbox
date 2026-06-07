"""
downloader — скачивание исходных файлов Банка России.

Домен работает через stratbox.base.net.download_bytes и не зависит напрямую от
конкретного HTTP-клиента или корпоративного сетевого шлюза.
"""

from __future__ import annotations

import re
import time

from stratbox.base.net import download_bytes
from stratbox.macrobanks.cbr_file_collector.contracts import (
    CbrDownloadedFileSource,
    CbrFileRegistryItem,
    CbrFileCollectFailure,
)
from stratbox.macrobanks.cbr_file_collector.file_names import resolve_download_file_name
from stratbox.macrobanks.cbr_file_collector.registry import DEFAULT_HEADERS


def build_cbr_url_variants(url: str) -> list[str]:
    variants: list[str] = []
    for banksector in ("BankSector", "banksector"):
        for mortgage in ("Mortgage", "mortgage"):
            for loans in ("Loans_to_corporations", "loans_to_corporations"):
                item = str(url)
                item = re.sub(r"/[Bb]ank[Ss]ector/", f"/{banksector}/", item)
                item = re.sub(r"/[Mm]ortgage/", f"/{mortgage}/", item)
                item = re.sub(r"/[Ll]oans_to_corporations/", f"/{loans}/", item)
                if item not in variants:
                    variants.append(item)

    if url in variants:
        variants.remove(url)
    return [url] + variants


def _headers_get(headers: dict[str, str] | None, key: str) -> str:
    if not headers:
        return ""
    key_low = key.lower()
    for k, v in headers.items():
        if str(k).lower() == key_low:
            return str(v)
    return ""


def _looks_like_html(content: bytes, headers: dict[str, str] | None) -> bool:
    content_type = _headers_get(headers, "Content-Type").lower()
    if "text/html" in content_type:
        return True
    head = (content or b"")[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _download_once(
    url: str,
    *,
    timeout_sec: int,
    min_bytes_ok: int,
    headers: dict[str, str] | None,
    plugin_only: bool,
):
    return download_bytes(
        url,
        timeout=timeout_sec,
        retries=0,
        backoff=0,
        min_bytes_ok=min_bytes_ok,
        headers=headers,
        plugin_only=plugin_only,
    )


def download_one_source(
    source: CbrFileRegistryItem,
    *,
    timeout_sec: int = 60,
    retry_attempts: int = 3,
    retry_backoff_sec: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
    try_case_variants: bool = True,
) -> CbrDownloadedFileSource | CbrFileCollectFailure:
    request_headers = headers or DEFAULT_HEADERS
    candidates = build_cbr_url_variants(source.url) if try_case_variants else [source.url]

    last_failure = CbrFileCollectFailure(
        source_id=source.source_id,
        url=source.url,
        error="No download attempt was made",
        attempts_used=0,
    )

    attempts_total = max(1, int(retry_attempts))
    for attempt in range(1, attempts_total + 1):
        for candidate_url in candidates:
            result = _download_once(
                candidate_url,
                timeout_sec=timeout_sec,
                min_bytes_ok=min_bytes_ok,
                headers=request_headers,
                plugin_only=plugin_only,
            )
            result_headers = getattr(result, "headers", None)

            if not result.ok or not result.content:
                last_failure = CbrFileCollectFailure(
                    source_id=source.source_id,
                    url=source.url,
                    error=result.error or "unknown download error",
                    status_code=result.status_code,
                    attempts_used=attempt,
                    used_url=candidate_url,
                    final_url=result.final_url,
                )
                continue

            if _looks_like_html(result.content, result_headers):
                last_failure = CbrFileCollectFailure(
                    source_id=source.source_id,
                    url=source.url,
                    error="Downloaded content looks like HTML page, not source file",
                    status_code=result.status_code,
                    attempts_used=attempt,
                    used_url=candidate_url,
                    final_url=result.final_url,
                )
                continue

            file_name = resolve_download_file_name(
                explicit_file_name=source.expected_file_name,
                headers=result_headers,
                url=candidate_url,
                fallback=f"{source.source_id or 'downloaded_file'}.xlsx",
            )
            return CbrDownloadedFileSource(
                source_id=source.source_id,
                url=source.url,
                file_name=file_name,
                content=result.content,
                size_bytes=len(result.content),
                used_url=candidate_url,
                final_url=result.final_url,
            )

        if attempt < attempts_total:
            time.sleep(retry_backoff_sec * attempt)

    return last_failure


def download_sources(
    sources: tuple[CbrFileRegistryItem, ...] | list[CbrFileRegistryItem],
    *,
    timeout_sec: int = 60,
    retry_attempts: int = 3,
    retry_backoff_sec: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
    try_case_variants: bool = True,
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> tuple[list[CbrDownloadedFileSource], list[CbrFileCollectFailure]]:
    iterator = list(sources)
    if show_progress:
        try:
            from tqdm.auto import tqdm
            progress_iter = tqdm(iterator, desc="CBR sources", leave=False)
        except Exception:
            progress_iter = iterator
    else:
        progress_iter = iterator

    downloaded: list[CbrDownloadedFileSource] = []
    failed: list[CbrFileCollectFailure] = []

    for source in progress_iter:
        item = download_one_source(
            source,
            timeout_sec=timeout_sec,
            retry_attempts=retry_attempts,
            retry_backoff_sec=retry_backoff_sec,
            min_bytes_ok=min_bytes_ok,
            headers=headers,
            plugin_only=plugin_only,
            try_case_variants=try_case_variants,
        )
        if isinstance(item, CbrDownloadedFileSource):
            downloaded.append(item)
            continue

        failed.append(item)
        if not continue_on_error:
            break

    return downloaded, failed


__all__ = [
    "build_cbr_url_variants",
    "download_one_source",
    "download_sources",
]
