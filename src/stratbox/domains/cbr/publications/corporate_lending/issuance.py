"""Discover official issuance publication assets from the selected index."""

from __future__ import annotations

from datetime import date
from posixpath import basename
from urllib.parse import unquote, urljoin, urlsplit

from stratbox.core.formats.html import link_targets

from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink
from stratbox.domains.cbr.publications.corporate_lending.issuance_editions import (
    SERIES_CODE, _FILENAME, report_date_from_filename, reference_period,
)

CBR_SORS_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/sors/"






def _bound(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    return date.fromisoformat(value) if isinstance(value, str) else value


def discover_links(html: bytes | str, *, index_url: str = CBR_SORS_INDEX_URL,
                   date_from: str | date | None = None,
                   date_to: str | date | None = None) -> tuple[IssuanceSourceLink, ...]:
    start, end = _bound(date_from), _bound(date_to)
    if start and end and start > end:
        raise ValueError("date_from is later than date_to")
    text = html.decode("utf-8-sig") if isinstance(html, bytes) else html
    by_date: dict[str, IssuanceSourceLink] = {}
    for href in link_targets(text):
        url = urljoin(index_url, href)
        name = unquote(basename(urlsplit(url).path))
        if _FILENAME.fullmatch(name) is None:
            continue
        report_date = report_date_from_filename(name)
        day = date.fromisoformat(report_date)
        if (start and day < start) or (end and day > end):
            continue
        item = IssuanceSourceLink(
            f"{SERIES_CODE}_{day:%Y%m%d}", url, name, report_date,
            reference_period(report_date),
        )
        previous = by_date.get(report_date)
        if previous is not None and previous.url != url:
            raise ValueError(f"Conflicting issuance sources for {report_date}")
        by_date[report_date] = item
    return tuple(by_date[k] for k in sorted(by_date))
