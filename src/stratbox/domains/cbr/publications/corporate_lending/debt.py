"""Discover official debt-stock publication assets from the selected index."""

from __future__ import annotations

from datetime import date, datetime
from posixpath import basename as posix_basename
from urllib.parse import urljoin, urlsplit

from stratbox.core.formats.html import link_targets

from stratbox.domains.cbr.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink
from stratbox.domains.cbr.publications.corporate_lending.debt_editions import (
    CBR_0105A_DEBT_CORP_SERIES_CODE, CBR_0105A_DEBT_CORP_FILENAME_RE, report_date_from_cbr_0105a_filename,
)


CBR_SORS_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/sors/"


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




def discover_cbr_0105a_debt_corp_links_from_html(
    html: bytes | str,
    *,
    index_url: str = CBR_SORS_INDEX_URL,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
) -> tuple[Cbr0105ADebtCorpSourceLink, ...]:
    """Extract the selected publication series from the supplied index HTML."""
    start = _parse_iso_date(date_from, field_name="date_from")
    end = _parse_iso_date(date_to, field_name="date_to")
    if start and end and start > end:
        raise ValueError(f"date_from must not be after date_to: {start} > {end}")

    text = html.decode("utf-8") if isinstance(html, bytes) else html
    by_date: dict[str, Cbr0105ADebtCorpSourceLink] = {}
    for href in link_targets(text):
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
