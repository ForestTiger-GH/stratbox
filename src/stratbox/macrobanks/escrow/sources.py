"""Discover escrow workbook links from the official publication index."""

from __future__ import annotations

import re
from hashlib import sha1
from posixpath import basename as posix_basename
from urllib.parse import urljoin, urlsplit

from stratbox.base.ioapi.html import link_targets

from stratbox.macrobanks._cbr import official_url
from stratbox.execution import OperationFailure
from stratbox.macrobanks.escrow.contracts import EscrowSourceLink

# Official CBR reports use both legacy VFS/document paths and the
# Collection/Collection/File publication archive.
ESCROW_SOURCE_ROOTS = (
    "/vfs/",
    "/content/document/file/",
    "/collection/collection/file/",
)


CBR_ESCROW_INDEX_URL = "https://www.cbr.ru/statistics/bank_sector/equity_const_financing/"
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



def discover_escrow_source_links(html: bytes, *, index_url: str = CBR_ESCROW_INDEX_URL) -> tuple[EscrowSourceLink, ...]:
    text = html.decode("utf-8")
    links: list[EscrowSourceLink] = []
    seen: set[str] = set()
    for href in link_targets(text):
        if not href.lower().endswith(".xlsx"):
            continue

        absolute = urljoin(index_url, href)
        try:
            official_url(absolute, roots=ESCROW_SOURCE_ROOTS)
        except OperationFailure:
            continue
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
