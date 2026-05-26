"""
sources — получение ссылок на ежемесячные Excel-файлы ЦБ по счетам эскроу.

Принцип:
- доменный код не знает про корпоративные шлюзы напрямую;
- страница и файлы скачиваются через stratbox.base.net.download_bytes();
- при наличии плагина URL будет переписан на уровне base.net.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from stratbox.base.net import download_bytes


CBR_ESCROW_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/equity_const_financing/"
CBR_BASE_URL = "https://www.cbr.ru"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_escrow_excel_links(
    *,
    index_url: str = CBR_ESCROW_INDEX_URL,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
) -> list[str]:
    """
    Возвращает список абсолютных ссылок на ежемесячные .xlsx по счетам эскроу.

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

    links: list[str] = []
    seen: set[str] = set()
    for node in soup.find_all("a", href=True):
        href = str(node["href"] or "").strip()
        if not href:
            continue
        if not href.lower().endswith(".xlsx"):
            continue

        absolute = urljoin(CBR_BASE_URL, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)

    return links


__all__ = [
    "CBR_ESCROW_INDEX_URL",
    "CBR_BASE_URL",
    "DEFAULT_HEADERS",
    "fetch_escrow_excel_links",
]
