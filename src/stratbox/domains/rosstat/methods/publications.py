"""Publication identification from explicit supplied index evidence."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from stratbox.shared.data.values import (Assessment, AssetSelection, IdentifiedMaterial, Material,
    PublicationAsset, PublicationListing, RequestSpec, UpdateAssessment, fingerprint)
from ..common.publication_rules import FamilyRule, parse_issue
from .links import parse_page_links


@dataclass(frozen=True)
class PublicationRules:
    source_id: str
    landing_url: str
    formats: frozenset[str]
    issue_rule: FamilyRule
    primary_asset: str


def request(inputs, settings: PublicationRules, context):
    locator = inputs.get("locator")
    if isinstance(locator, PublicationAsset):
        if locator.source_id != settings.source_id:
            raise ValueError("rosstat.asset_source_conflict")
        name = PurePosixPath(urlsplit(locator.locator).path).name
        parsed_issue, _, conflicts = parse_issue(settings.issue_rule, name, str(locator.metadata.get("label", "")))
        parsed_asset, _, _ = settings.issue_rule.asset_id(str(locator.metadata.get("label", "")), name)
        if conflicts or parsed_issue != locator.issue_id or parsed_asset != locator.asset_id:
            raise ValueError("rosstat.asset_identity_conflict")
        url, issue, asset = locator.locator, locator.issue_id, locator.asset_id
        format = locator.format
    else:
        url = locator if isinstance(locator, str) else settings.landing_url
        issue, asset = str(context.parameters.get("issue_id", "")), "index"
        format = "html"
    if not _official(url) or (asset != "index" and not _file_url(url)):
        raise ValueError("rosstat.official_url_required")
    return {"request": RequestSpec(url, max_bytes=int(context.parameters.get("max_bytes", 100 * 1024 * 1024)),
        source_id=settings.source_id, metadata={"issue_id": issue, "asset_id": asset, "format": format})}


def _official(url):
    parts = urlsplit(url)
    return (parts.scheme == "https" and parts.hostname in {"rosstat.gov.ru", "www.rosstat.gov.ru"}
        and parts.username is None and parts.password is None and parts.port in {None, 443})


def _file_url(url):
    from urllib.parse import unquote
    parts = urlsplit(url)
    return _official(url) and not parts.query and unquote(parts.path).startswith(("/storage/mediabank/", "/upload/"))


def scan(inputs, settings: PublicationRules, context):
    material = inputs["index"]
    if not isinstance(material, Material):
        raise TypeError("rosstat.index_material_required")
    if material.source_id not in {None, settings.source_id, settings.source_id + ".index"}:
        raise ValueError("rosstat.index_source_conflict")
    if material.media_type not in {"text/html", "application/xhtml+xml", "application/octet-stream"}:
        raise ValueError("rosstat.index_media_type_invalid")
    links = parse_page_links(material.data.decode(material.charset or "utf-8"), settings.landing_url, _official)
    entries, findings = [], []
    for link in links:
        context.checkpoint()
        name = PurePosixPath(urlsplit(link.url).path).name
        extension = name.rsplit(".", 1)[-1].casefold() if "." in name else ""
        if extension not in settings.formats:
            if "download" in link.raw_href.casefold() or "/storage/" in link.raw_href.casefold():
                findings.append("unclassified_asset:" + link.raw_href)
            continue
        if not _file_url(link.url):
            findings.append("asset_external_origin:" + link.raw_href)
            continue
        issue, evidence, conflicts = parse_issue(settings.issue_rule, name, link.label_literal)
        asset, role, asset_evidence = settings.issue_rule.asset_id(link.label_literal, name)
        if issue is None or asset is None:
            findings.extend(conflicts or ("asset_identity_unresolved:" + link.raw_href,))
            continue
        entries.append(PublicationAsset(settings.source_id, issue, asset, link.url, extension,
            {"label": link.label_literal, "raw_href": link.raw_href, "position": link.position,
             "issue_evidence": evidence, "asset_role": role, "asset_evidence": asset_evidence,
             "index_identity": material.identity.sha256}))
    keys = {(entry.source_id, entry.issue_id, entry.asset_id, entry.locator) for entry in entries}
    if len(keys) != len(entries):
        entries = list({(e.source_id, e.issue_id, e.asset_id, e.locator): e for e in entries}.values())
    assessment = Assessment("partial" if findings else "unknown", tuple(findings),
        observed=tuple(entry.issue_id + ":" + entry.asset_id for entry in entries),
        qualifications=frozenset({"observed_index_scope", "publisher_inventory_not_certified"}))
    listing = PublicationListing("rosstat", tuple(entries), assessment, (material.identity,))
    return {"listing": listing, "coverage": assessment}


def select(inputs, settings: PublicationRules, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing) or listing.domain_id != "rosstat":
        raise TypeError("rosstat.publication_listing_required")
    query = inputs.get("query", context.parameters)
    query = query if hasattr(query, "get") else {}
    issue = query.get("issue_id", query.get("issue"))
    candidates = tuple(entry for entry in listing.entries if entry.source_id == settings.source_id)
    if issue is None and candidates:
        issue = max(entry.issue_id for entry in candidates)
    candidates = tuple(entry for entry in candidates if entry.issue_id == issue)
    requested_asset = query.get("asset_id", settings.primary_asset)
    matches = tuple(entry for entry in candidates if entry.asset_id == requested_asset)
    if len({entry.locator for entry in matches}) > 1:
        raise ValueError("rosstat.asset_selection_ambiguous")
    assessment = Assessment("complete" if len(matches) == 1 else "unknown",
        () if matches else ("requested_asset_not_observed",),
        expected=(str(issue) + ":" + requested_asset,),
        observed=tuple(e.issue_id + ":" + e.asset_id for e in matches),
        qualifications=frozenset({"latest_observed_only"}) if not query.get("issue_id", query.get("issue")) else frozenset())
    return {"selection": AssetSelection(matches, assessment)}


def assess(inputs, settings, context):
    evidence, baseline = inputs["evidence"], inputs.get("baseline")
    if isinstance(evidence, IdentifiedMaterial):
        evidence = evidence.material
    if isinstance(baseline, IdentifiedMaterial):
        baseline = baseline.material
    if isinstance(evidence, Material):
        candidate = evidence.identity.sha256
        previous = baseline.identity.sha256 if isinstance(baseline, Material) else baseline
        state = "first_seen" if previous is None else "unchanged" if previous == candidate else "changed"
        return {"assessment": UpdateAssessment(state, "exact_material_bytes", predecessor=previous, candidate=candidate)}
    if not isinstance(evidence, PublicationListing):
        raise TypeError("rosstat.source_evidence_required")
    candidate = fingerprint(tuple(sorted((e.issue_id, e.asset_id, e.locator) for e in evidence.entries)))
    previous = fingerprint(tuple(sorted((e.issue_id, e.asset_id, e.locator) for e in baseline.entries))) if isinstance(baseline, PublicationListing) else None
    # A partial index cannot establish disappearance or unchanged file bytes.
    # Reordering or relocation is evidence about the index, not a revision proof.
    status = "indeterminate"
    findings = (*evidence.assessment.findings, "publisher_inventory_or_material_bytes_not_established")
    return {"assessment": UpdateAssessment(status, "observed_index_scope", findings,
        predecessor=previous, candidate=candidate)}
