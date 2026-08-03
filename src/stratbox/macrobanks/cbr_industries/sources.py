"""Обнаружение официальных файлов серии ``01_05_A_Debt_corp``."""

from __future__ import annotations

import re
from datetime import date, datetime
from posixpath import basename as posix_basename
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from stratbox.base.net import download_bytes
from stratbox.macrobanks.cbr_industries.contracts import Cbr0105ADebtCorpSourceLink
from stratbox.macrobanks.cbr_industries.schema import CBR_0105A_DEBT_CORP_SERIES_CODE


CBR_SORS_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/sors/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
CBR_0105A_DEBT_CORP_FILENAME_RE = re.compile(
    r"^01_05_A_Debt_corp_(\d{8})\.xlsx$",
    flags=re.I,
)


def _parse_iso_date(value: str | date | None, *, field_name: str) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO date YYYY-MM-DD: {value!r}") from exc


def report_date_from_cbr_0105a_filename(source_name: str) -> str:
    """Извлекает ISO-дату из канонического имени ``01_05_A_Debt_corp``."""
    match = CBR_0105A_DEBT_CORP_FILENAME_RE.fullmatch(str(source_name).strip())
    if not match:
        raise ValueError(f"Unsupported 01_05_A_Debt_corp source name: {source_name!r}")
    parsed = datetime.strptime(match.group(1), "%Y%m%d").date()
    return parsed.isoformat()


def discover_cbr_0105a_debt_corp_links_from_html(
    html: bytes | str,
    *,
    index_url: str = CBR_SORS_INDEX_URL,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
) -> tuple[Cbr0105ADebtCorpSourceLink, ...]:
    """Извлекает только ссылки заданной серии из HTML официальной страницы."""
    start = _parse_iso_date(date_from, field_name="date_from")
    end = _parse_iso_date(date_to, field_name="date_to")
    if start and end and start > end:
        raise ValueError(f"date_from must not be after date_to: {start} > {end}")

    soup = BeautifulSoup(html, "html.parser")
    by_date: dict[str, Cbr0105ADebtCorpSourceLink] = {}
    for node in soup.find_all("a", href=True):
        href = str(node.get("href") or "").strip()
        if not href:
            continue
        absolute = urljoin(index_url, href)
        source_name = posix_basename(urlsplit(absolute).path or "")
        if not CBR_0105A_DEBT_CORP_FILENAME_RE.fullmatch(source_name):
            continue

        report_date = report_date_from_cbr_0105a_filename(source_name)
        report_day = date.fromisoformat(report_date)
        if start and report_day < start:
            continue
        if end and report_day > end:
            continue

        source = Cbr0105ADebtCorpSourceLink(
            source_id=f"{CBR_0105A_DEBT_CORP_SERIES_CODE}_{report_day.strftime('%Y%m%d')}",
            url=absolute,
            source_name=source_name,
            report_date=report_date,
        )
        previous = by_date.get(report_date)
        if previous is not None and previous.url != source.url:
            raise ValueError(
                "Multiple different 01_05_A_Debt_corp links found for one report date: "
                f"date={report_date}, urls={[previous.url, source.url]}"
            )
        by_date[report_date] = source

    return tuple(by_date[key] for key in sorted(by_date))


def discover_cbr_0105a_debt_corp_source_links(
    *,
    index_url: str = CBR_SORS_INDEX_URL,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
) -> tuple[Cbr0105ADebtCorpSourceLink, ...]:
    """Получает официальный каталог источников выбранного периода."""
    result = download_bytes(
        index_url,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        min_bytes_ok=min_bytes_ok,
        headers=headers or DEFAULT_HEADERS,
        plugin_only=plugin_only,
    )
    if not result.ok or not result.content:
        raise RuntimeError(
            "Failed to fetch CBR sors index page for 01_05_A_Debt_corp: "
            f"{result.error or 'unknown error'}"
        )
    return discover_cbr_0105a_debt_corp_links_from_html(
        result.content,
        index_url=index_url,
        date_from=date_from,
        date_to=date_to,
    )


__all__ = [
    "CBR_0105A_DEBT_CORP_FILENAME_RE",
    "CBR_SORS_INDEX_URL",
    "DEFAULT_HEADERS",
    "discover_cbr_0105a_debt_corp_links_from_html",
    "discover_cbr_0105a_debt_corp_source_links",
    "report_date_from_cbr_0105a_filename",
]
