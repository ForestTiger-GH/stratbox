"""Discover escrow workbook links from the official publication index."""

from __future__ import annotations

import re
from datetime import date
from hashlib import sha1
from posixpath import basename as posix_basename
from urllib.parse import urljoin, urlsplit

from stratbox.core.formats.html import link_targets

from stratbox.domains.cbr.publications.access import official_url
from stratbox.core.execution import OperationFailure
from stratbox.domains.cbr.publications.project_finance.contracts import EscrowSourceLink

# Official CBR reports use both legacy VFS/document paths and the
# Collection/Collection/File publication archive.
ESCROW_SOURCE_ROOTS = (
    "/vfs/",
    "/content/document/file/",
    "/collection/collection/file/",
    "/analytics/finansirovanie-dolevogo-stroitelstva/",
)


CBR_ESCROW_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/equity_const_financing/"
_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")
_HTML_ISSUE_RE = re.compile(r"^/analytics/finansirovanie-dolevogo-stroitelstva/(\d{4}-\d{2}-\d{2})/?$", re.I)


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



def discover_escrow_source_links(html: bytes, *, index_url: str = CBR_ESCROW_INDEX_URL) -> tuple[EscrowSourceLink, ...]:
    text = html.decode("utf-8")
    links: list[EscrowSourceLink] = []
    seen: set[str] = set()
    for href in link_targets(text):
        absolute = urljoin(index_url, href)
        path = urlsplit(absolute).path
        html_issue = _HTML_ISSUE_RE.fullmatch(path)
        if not path.lower().endswith(".xlsx") and html_issue is None:
            continue
        if html_issue is not None:
            try:
                date.fromisoformat(html_issue.group(1))
            except ValueError:
                continue
        try:
            official_url(absolute, roots=ESCROW_SOURCE_ROOTS)
        except OperationFailure:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        source_name = _source_name_from_url(absolute) if html_issue is None else f"escrow_{html_issue.group(1)}.html"
        links.append(
            EscrowSourceLink(
                source_id=_source_id_from_absolute_url(absolute),
                url=absolute,
                source_name=source_name,
                file_date_hint=_date_hint_from_name(source_name) if html_issue is None else html_issue.group(1),
                format="xlsx" if html_issue is None else "html",
                extraction_status="supported" if html_issue is None else "unsupported_layout",
                profile_id="cbr-escrow-xlsx-flake-2" if html_issue is None else "cbr-escrow-historical-html",
            )
        )

    return tuple(links)
