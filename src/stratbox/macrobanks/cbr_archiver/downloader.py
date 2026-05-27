"""
downloader — скачивание исходных файлов Банка России.

Принципиально важно:
- домен не использует requests напрямую;
- каждый URL проходит через stratbox.base.net.download_bytes();
- при наличии stratbox-plugin корпоративные шлюзы применяются на уровне base.net;
- содержимое скачанных файлов не меняется.
"""

from __future__ import annotations

import re

from stratbox.base.net import download_bytes
from stratbox.macrobanks.cbr_archiver.models import (
    CbrArchiveSource,
    CbrDownloadFailure,
    CbrDownloadedFile,
)
from stratbox.macrobanks.cbr_archiver.naming import resolve_download_file_name
from stratbox.macrobanks.cbr_archiver.registry import DEFAULT_HEADERS


def build_cbr_url_variants(url: str) -> list[str]:
    """Строит варианты URL с разным регистром ключевых каталогов сайта ЦБ."""
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
    """Возвращает HTTP-заголовок без чувствительности к регистру."""
    if not headers:
        return ""
    key_low = key.lower()
    for k, v in headers.items():
        if str(k).lower() == key_low:
            return str(v)
    return ""


def _looks_like_html(content: bytes, headers: dict[str, str] | None) -> bool:
    """Проверяет, не вернул ли сайт HTML-страницу вместо файла."""
    content_type = _headers_get(headers, "Content-Type").lower()
    if "text/html" in content_type:
        return True

    head = (content or b"")[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def download_one_source(
    source: CbrArchiveSource,
    *,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
    try_case_variants: bool = True,
) -> CbrDownloadedFile | CbrDownloadFailure:
    """Скачивает один источник ЦБ и возвращает файл или ошибку."""
    request_headers = headers or DEFAULT_HEADERS
    candidates = build_cbr_url_variants(source.url) if try_case_variants else [source.url]

    last_failure = CbrDownloadFailure(source=source, error="No download attempt was made")

    for candidate_url in candidates:
        result = download_bytes(
            candidate_url,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            min_bytes_ok=min_bytes_ok,
            headers=request_headers,
            plugin_only=plugin_only,
        )
        result_headers = getattr(result, "headers", None)

        if not result.ok or not result.content:
            last_failure = CbrDownloadFailure(
                source=source,
                error=result.error or "unknown download error",
                status_code=result.status_code,
                used_url=candidate_url,
                final_url=result.final_url,
            )
            continue

        if _looks_like_html(result.content, result_headers):
            last_failure = CbrDownloadFailure(
                source=source,
                error="Downloaded content looks like HTML page, not source file",
                status_code=result.status_code,
                used_url=candidate_url,
                final_url=result.final_url,
            )
            continue

        file_name = resolve_download_file_name(
            explicit_file_name=source.file_name,
            headers=result_headers,
            url=candidate_url,
            fallback=f"{source.code or 'downloaded_file'}.xlsx",
        )
        return CbrDownloadedFile(
            source=source,
            file_name=file_name,
            content=result.content,
            size_bytes=len(result.content),
            used_url=candidate_url,
            final_url=result.final_url,
        )

    return last_failure


def download_sources(
    sources: list[CbrArchiveSource],
    *,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
    try_case_variants: bool = True,
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> tuple[list[CbrDownloadedFile], list[CbrDownloadFailure]]:
    """Скачивает список источников ЦБ."""
    iterator = sources
    if show_progress:
        try:
            from tqdm.auto import tqdm

            iterator = tqdm(sources, desc="CBR sources", leave=False)
        except Exception:
            iterator = sources

    downloaded: list[CbrDownloadedFile] = []
    failed: list[CbrDownloadFailure] = []

    for source in iterator:
        item = download_one_source(
            source,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            min_bytes_ok=min_bytes_ok,
            headers=headers,
            plugin_only=plugin_only,
            try_case_variants=try_case_variants,
        )
        if isinstance(item, CbrDownloadedFile):
            downloaded.append(item)
            continue

        failed.append(item)
        if not continue_on_error:
            raise RuntimeError(f"Failed to download CBR source: {source.url} :: {item.error}")

    return downloaded, failed


__all__ = [
    "build_cbr_url_variants",
    "download_one_source",
    "download_sources",
]
