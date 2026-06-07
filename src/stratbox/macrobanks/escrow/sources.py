"""
sources — получение ссылок на ежемесячные Excel-файлы ЦБ по счетам эскроу.

Принцип:
- доменный код не знает про корпоративные шлюзы напрямую;
- страница и файлы скачиваются через stratbox.base.net.download_bytes();
- при наличии плагина URL будет переписан на уровне base.net.
"""

from __future__ import annotations

import re
from hashlib import sha1
from posixpath import basename as posix_basename
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from stratbox.base.net import download_bytes
from stratbox.macrobanks.escrow.contracts import EscrowSourceLink


CBR_ESCROW_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/equity_const_financing/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")


def _source_name_from_url(url: str) -> str:
    path = urlsplit(str(url)).path or ""
    name = posix_basename(path)
    return name or "escrow_source.xlsx"



def _source_id_from_absolute_url(url: str) -> str:
    path = urlsplit(str(url)).path or ""
    stem = posix_basename(path)
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", stem).strip("_").lower() or "escrow_source"
    digest = sha1(str(url).encode("utf-8")).hexdigest()[:8]
    return f"{slug}_{digest}"


def _date_hint_from_name(name: str) -> str | None:
    match = _DATE_RE.search(str(name))
    if not match:
        return None
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"



def discover_escrow_source_links(
    *,
    index_url: str = CBR_ESCROW_INDEX_URL,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
) -> tuple[EscrowSourceLink, ...]:
    """
    Возвращает структурированный список ссылок на ежемесячные .xlsx по счетам эскроу.

    Ссылки возвращаются в том порядке, в котором они встретились на странице.
    Дубликаты удаляются без потери исходного порядка.
    """
    download = download_bytes(
        index_url,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
    )
    if not download.ok or not download.content:
        raise RuntimeError(
            f"Failed to fetch escrow index page: {download.error or 'unknown error'}"
        )

    soup = BeautifulSoup(download.content, "html.parser")

    links: list[EscrowSourceLink] = []
    seen: set[str] = set()
    for node in soup.find_all("a", href=True):
        href = str(node["href"] or "").strip()
        if not href:
            continue
        if not href.lower().endswith(".xlsx"):
            continue

        absolute = urljoin(index_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        source_name = _source_name_from_url(absolute)
        links.append(
            EscrowSourceLink(
                source_id=_source_id_from_absolute_url(absolute),
                url=absolute,
                source_name=source_name,
                file_date_hint=_date_hint_from_name(source_name),
            )
        )

    return tuple(links)



__all__ = [
    "CBR_ESCROW_INDEX_URL",
    "DEFAULT_HEADERS",
    "discover_escrow_source_links",
]
