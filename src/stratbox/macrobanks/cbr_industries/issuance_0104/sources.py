"""Exact discovery and reference-month semantics of the CBR 01_04_A series."""

from __future__ import annotations

import re
from datetime import date, datetime
from posixpath import basename
from urllib.parse import unquote, urljoin, urlsplit

from stratbox.base.ioapi.html import link_targets

from .contracts import IssuanceSourceLink

SERIES_CODE = "01_04_A_New_loans_corp"
CBR_SORS_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/sors/"
_FILENAME = re.compile(r"01_04_A_New_loans_corp_(\d{8})\.xlsx", re.I)


def report_date_from_filename(name: str) -> str:
    match = _FILENAME.fullmatch(name)
    if match is None:
        raise ValueError(f"Unknown issuance filename: {name!r}")
    day = datetime.strptime(match.group(1), "%Y%m%d").date()
    if day.day != 1:
        raise ValueError(f"Issuance release date is not the first day of a month: {name!r}")
    return day.isoformat()


def reference_period(report_date: str) -> str:
    day = date.fromisoformat(report_date)
    if day.day != 1:
        raise ValueError("Issuance report date must be the first day of a month")
    year, month = (day.year - 1, 12) if day.month == 1 else (day.year, day.month - 1)
    return f"{year:04d}-{month:02d}"


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
