"""Publisher inventory recognition, separate from operation orchestration."""
from dataclasses import replace
from datetime import date, datetime
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urljoin, urlsplit

from stratbox.core.execution import OperationFailure
from stratbox.core.formats.html import link_targets
from stratbox.core.operations.source.validation import use_payload
from stratbox.domains.cbr.publications.access import HTML_TYPES, official_url, receive_cbr, validate_workbook
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.source_publications import SourceAssetIdentity
from .contracts import IdentifiedOriginal, PublicationAsset, PublicationInventory
from .profiles import acquisition_profile
from .catalog import source


def _profile(series_id):
    try:
        item = source(series_id)
        return item, acquisition_profile(item.acquisition_profile)
    except ValueError as error:
        raise OperationFailure(str(error)) from None


def discover_value(req, invocation, *, transport=None):
    item, profile = _profile(req.series_id)
    if type(req.max_links) is not int or not 0 < req.max_links <= 100_000:
        raise OperationFailure("cbr.inventory.limit_invalid")
    page = profile.default_url if req.page_url is None else req.page_url
    official_url(page)
    invocation.stage("discover")
    if req.index is None and profile.kind in {"fixed", "page"}:
        return PublicationInventory(item.series_id, (PublicationAsset(item.series_id, None,
            "main", page, item.formats[0], "registered_route", item.extraction_profile),), None,
            SnapshotCoverage("unknown", "A declared acquisition route; availability and publication history are unverified."))
    if req.index is None:
        payload = receive_cbr(page, roots=(), media_types=HTML_TYPES, limit=8 * 1024**2,
            source_id=item.series_id, transport=transport, invocation=invocation).payload
    else:
        payload = req.index
    use_payload(payload, invocation, role="publication_index", limit=8 * 1024**2)
    try:
        html = payload.data.decode(payload.charset or "utf-8-sig")
    except (UnicodeError, LookupError):
        raise OperationFailure("cbr.inventory.encoding_invalid") from None
    if "<" not in html or ">" not in html:
        raise OperationFailure("cbr.inventory.html_invalid")
    links = link_targets(html)
    if len(links) > req.max_links:
        raise OperationFailure("cbr.inventory.link_limit")
    pattern = re.compile(profile.filename_pattern, re.I) if profile.filename_pattern else None
    assets, seen, logical, rejected = [], set(), {}, 0
    for href in links:
        invocation.check_cancelled()
        try:
            url = urljoin(page, href)
            name = unquote(PurePosixPath(urlsplit(url).path).name)
        except ValueError:
            rejected += 1
            continue
        issue, extraction, fmt = None, item.extraction_profile, "xlsx"
        if pattern is not None:
            match = pattern.fullmatch(name)
            if match is None:
                continue
            try:
                issue = datetime.strptime(match.group("date"), "%Y%m%d").date().isoformat()
            except ValueError:
                rejected += 1
                continue
            fmt = name.rsplit(".", 1)[-1].lower()
        elif profile.kind == "territorial_index":
            match = re.fullmatch(r"DivisionsPerRegion_(\d{2})(\d{2})(\d{2})\.xlsx", name, re.I)
            if match is None:
                continue
            try:
                issue = date(2000 + int(match[3]), int(match[2]), int(match[1])).isoformat()
            except ValueError:
                rejected += 1
                continue
        elif profile.kind == "escrow_index":
            path = urlsplit(url).path
            historical = re.fullmatch(r"/analytics/finansirovanie-dolevogo-stroitelstva/(\d{4}-\d{2}-\d{2})/?", path, re.I)
            if historical is not None:
                try:
                    issue = date.fromisoformat(historical[1]).isoformat()
                except ValueError:
                    rejected += 1
                    continue
                fmt, extraction = "html", None
            elif name.lower().endswith(".xlsx"):
                match = re.search(r"(\d{2})(\d{2})(\d{4})", name)
                if match:
                    try:
                        issue = date(int(match[3]), int(match[2]), int(match[1])).isoformat()
                    except ValueError:
                        rejected += 1
                        continue
            else:
                continue
        elif profile.kind == "fixed":
            if name.casefold() != unquote(PurePosixPath(urlsplit(profile.default_url).path).name).casefold():
                continue
            fmt = item.formats[0]
        else:
            continue
        try:
            official_url(url)
        except OperationFailure:
            rejected += 1
            continue
        if url in seen:
            continue
        seen.add(url)
        recognition = ("registered_variant" if extraction is not None else
            "unsupported_layout" if profile.kind == "escrow_index" and fmt == "html" else
            "original_only")
        key = (issue, "main", fmt)
        # A dated publication may be linked from several publisher paths.
        # Keep those paths as unresolved alternatives, not extra releases.
        # Undated candidates stay independent until the issue is identified.
        if issue is not None and key in logical:
            index = logical[key]
            assets[index] = replace(assets[index],
                alternative_urls=assets[index].alternative_urls + (url,))
        else:
            if issue is not None:
                logical[key] = len(assets)
            assets.append(PublicationAsset(item.series_id, issue, "main", url, fmt,
                recognition, extraction))
    return PublicationInventory(item.series_id, tuple(assets), payload.identity,
        SnapshotCoverage("unknown", "Matching links in one supplied or acquired index; completeness of historical inventory is unspecified."), rejected)
