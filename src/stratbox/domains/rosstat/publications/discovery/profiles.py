"""Bounded candidate recognition routed to four uncalibrated family profiles.

The source landing HTML must be captured live before a profile can claim a
complete publisher inventory. Current discovery returns candidates for explicit
acquisition, NEVER an authoritative latest/absence statement.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urlsplit

from stratbox.domains.rosstat._source import allowed_file_url, allowed_rosstat_base
from .links import parse_page_links
from .coverage import assess
from .families import RULES
from .families.rules import parse_issue
from ..catalog import get_rosstat_source
from ..contracts import AssetKey, DiscoveredAsset, IssueKey, RosstatPublicationIndex
from stratbox.shared.evidence import AcquisitionReceipt, SourcePayload

_FILE_END = re.compile(r"\.(pdf|xlsx|zip|rar)\Z", re.I)
_POTENTIAL = re.compile(r"(download|file|archive|attachment|скачат|загруз|таблиц|бюллетен)", re.I)


def profile_for(series_id: str):
    spec = get_rosstat_source(series_id)
    return RULES[spec.discovery_profile_id]


def _format(url: str) -> str | None:
    try:
        path = unquote(urlsplit(url).path)
    except (ValueError, TypeError):
        return None
    match = _FILE_END.search(path)
    return match.group(1).lower() if match else None


def qualify_index(
    series_id: str, payload: SourcePayload, *, text: str,
    acquisition: AcquisitionReceipt | None = None,
) -> RosstatPublicationIndex:
    spec = get_rosstat_source(series_id)
    rule = profile_for(series_id)
    links = parse_page_links(text, spec.landing_url, allowed_rosstat_base)
    candidates: list[DiscoveredAsset] = []
    unclassified = 0
    for link in links:
        fmt = _format(link.url)
        if fmt not in spec.accepted_formats:
            if fmt or _POTENTIAL.search(link.url) or _POTENTIAL.search(link.label_literal):
                unclassified += 1
            continue
        if not allowed_file_url(link.url):
            unclassified += 1
            continue
        filename = PurePosixPath(unquote(urlsplit(link.url).path)).name
        issue_id, issue_evidence, diagnostics = parse_issue(rule, filename, link.label_literal)
        asset_id, role, role_evidence = rule.asset_id(link.label_literal, filename)
        if asset_id is None:
            diagnostics = diagnostics + ("asset_identity_unresolved",)
        key = AssetKey(IssueKey(series_id, issue_id), asset_id) if issue_id and asset_id else None
        candidates.append(DiscoveredAsset(
            key, role, link.url, filename, link.label_literal, link.raw_href,
            fmt, spec.landing_url, payload.identity, rule.profile_version,
            link.position, "qualified" if key is not None else "ambiguous",
            issue_label=link.label_literal, issue_evidence=issue_evidence or role_evidence,
            diagnostic_codes=diagnostics,
        ))
    if not candidates:
        raise ValueError("rosstat.index_unrecognized")
    # One candidate may be present repeatedly in navigation; same URL/key is
    # one logical attachment. Distinct URLs for one key stay unresolved.
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
            ambiguous.append(replace(
                item, qualification="ambiguous",
                diagnostic_codes=item.diagnostic_codes + ("asset_collision",)
                if item.key is not None else item.diagnostic_codes,
            ))
    unresolved = len(ambiguous) + unclassified
    assessment = assess(
        series_id=series_id, profile_id=rule.profile_id,
        profile_version=rule.profile_version, index_sha256=payload.identity.sha256,
        qualified=len(qualified), unresolved=unresolved,
        reasons=("publisher_layout_not_calibrated",)
        + (("unrecognized_links",) if unclassified else ())
        + (("ambiguous_assets",) if ambiguous else ()),
    )
    return RosstatPublicationIndex(
        series_id, spec.landing_url, payload.identity, rule.profile_version,
        tuple(sorted(qualified, key=lambda a: (a.key.issue.issue_id, a.key.asset_id, a.url))),
        tuple(sorted(ambiguous, key=lambda a: a.position)),
        unclassified, assessment,
        acquisition=acquisition,
        source_kind="publisher_http" if acquisition is not None else "supplied_payload",
    )
