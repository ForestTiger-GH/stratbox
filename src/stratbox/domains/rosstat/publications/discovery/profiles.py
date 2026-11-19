"""Conservative, provisional source-specific recognition of Rosstat issue links.

The actual four page layouts must be calibrated on real publisher HTML. Any
unrecognized candidate remains visible as ambiguity rather than becoming a
fabricated release or an automatic download.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urlsplit

from stratbox.domains.rosstat._source import allowed_file_url, allowed_page_url
from .links import PageLink, parse_page_links
from ..catalog import get_rosstat_source
from ..contracts import AssetKey, DiscoveredAsset, IssueKey, RosstatPublicationIndex
from stratbox.shared.evidence import SourcePayload

PROFILE_VERSION = "rosstat-provisional-links-1"
_YEAR_MONTH = re.compile(r"(?<!\d)(20\d{2})[-_. /](0?[1-9]|1[0-2])(?!\d)")
_MONTH_YEAR = re.compile(r"(?<!\d)(0?[1-9]|1[0-2])[-_. /](20\d{2})(?!\d)")
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_FILE_END = re.compile(r"\.(pdf|xlsx|zip|rar)\Z", re.I)


def _issue_id(series_id: str, label: str, filename: str) -> str | None:
    text = filename + " " + label
    if series_id == "rosstat.population_municipalities":
        years = _YEAR.findall(text)
        return years[0] if years and len(set(years)) == 1 else None
    # Some publisher archives use MM-YYYY rather than YYYY-MM.
    if series_id == "rosstat.socioeconomic_regions":
        match = _MONTH_YEAR.search(text)
        if match is not None:
            return f"{match.group(2)}-{int(match.group(1)):02d}"
    match = _YEAR_MONTH.search(text)
    if match is not None:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    match = _MONTH_YEAR.search(text)
    if match is not None:
        return f"{match.group(2)}-{int(match.group(1)):02d}"
    return None


def _role(label: str, filename: str) -> str:
    text = (label + " " + filename).casefold()
    if any(word in text for word in ("приложен", "appendix", "annex")):
        return "annex"
    return "primary"


def _format(url: str) -> str | None:
    try:
        path = unquote(urlsplit(url).path)
    except (ValueError, TypeError):
        return None
    match = _FILE_END.search(path)
    return match.group(1).lower() if match else None


def qualify_index(series_id: str, payload: SourcePayload, *, text: str) -> RosstatPublicationIndex:
    spec = get_rosstat_source(series_id)
    links = parse_page_links(
        text, spec.landing_url,
        lambda url: allowed_page_url(url, spec.landing_url),
    )
    candidates: list[DiscoveredAsset] = []
    unclassified = 0
    for link in links:
        fmt = _format(link.url)
        if fmt not in spec.accepted_formats:
            # Unrelated page links do not belong to the candidate inventory.
            continue
        if not allowed_file_url(link.url):
            unclassified += 1
            continue
        filename = PurePosixPath(unquote(urlsplit(link.url).path)).name
        issue_id = _issue_id(series_id, link.label_literal, filename)
        role = _role(link.label_literal, filename)
        key = AssetKey(IssueKey(series_id, issue_id), role) if issue_id else None
        candidates.append(DiscoveredAsset(
            key, role, link.url, filename, link.label_literal, link.raw_href,
            fmt, spec.landing_url, payload.identity, PROFILE_VERSION, link.position,
            "qualified" if key else "ambiguous",
        ))
    if not candidates:
        raise ValueError("rosstat.index_unrecognized")
    # Collapse repeated exact references; retain source occurrence as first evidence.
    distinct = {}
    for item in candidates:
        distinct.setdefault((item.key, item.url, item.declared_format), item)
    grouped = defaultdict(list)
    for item in distinct.values():
        if item.key is not None:
            grouped[item.key].append(item)
    qualified, ambiguous = [], []
    for item in distinct.values():
        if item.key is not None and len(grouped[item.key]) == 1:
            qualified.append(item)
        else:
            ambiguous.append(replace(item, qualification="ambiguous"))
    # Do not advertise authoritative absence when an index has no qualified assets.
    coverage = "unknown" if not qualified and not ambiguous else (
        "partial" if ambiguous or unclassified else "complete"
    )
    return RosstatPublicationIndex(
        series_id, spec.landing_url, payload.identity, PROFILE_VERSION,
        tuple(sorted(qualified, key=lambda a: (a.key.issue.issue_id, a.key.asset_id, a.url))),
        tuple(sorted(ambiguous, key=lambda a: a.position)),
        unclassified, coverage,
    )
