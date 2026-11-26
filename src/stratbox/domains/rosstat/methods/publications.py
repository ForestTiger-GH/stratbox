"""Publication identification from explicit supplied index evidence."""
from __future__ import annotations

from dataclasses import dataclass, replace
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
    selection = inputs.get("selection")
    if selection is not None:
        if not isinstance(selection, AssetSelection) or not selection.assessment.complete or len(selection.entries) != 1:
            raise ValueError("rosstat.request_single_qualified_asset_required")
        if locator is not None and locator != selection.entries[0]:
            raise ValueError("rosstat.asset_identity_conflict")
        locator = selection.entries[0]
    query = inputs.get("query")
    parameters = dict(context.parameters)
    if isinstance(query, dict) or hasattr(query, "items"):
        parameters.update(query)
    role = parameters.get("role", "asset" if isinstance(locator, PublicationAsset) else "index")
    if role not in {"index", "asset"}:
        raise ValueError("rosstat.request_role_invalid")
    if role == "index" and isinstance(locator, PublicationAsset):
        raise ValueError("rosstat.index_asset_conflict")
    if role == "asset" and not isinstance(locator, PublicationAsset):
        raise ValueError("rosstat.request_asset_required")
    if isinstance(locator, PublicationAsset):
        if locator.source_id != settings.source_id or locator.format not in settings.formats:
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
        issue, asset = "", "index"
        format = "html"
    if not _official(url) or (asset != "index" and not _file_url(url)):
        raise ValueError("rosstat.official_url_required")
    return {"request": RequestSpec(url, max_bytes=int(context.parameters.get("max_bytes", 100 * 1024 * 1024)),
        source_id=settings.source_id if role == "asset" else settings.source_id + ".index",
        metadata={"issue_id": issue, "asset_id": asset, "format": format, "role": role})}


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
             "issue_order": tuple(int(part) for part in issue.split("-")),
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
    from stratbox.shared.data.selection import IssueQuery, issue_query, select_publication_assets
    keys = set(IssueQuery.__dataclass_fields__) | {"source_id", "asset_id", "issue_id", "issue", "as_of", "periods", "format", "locator", "url"}
    query = issue_query(inputs.get("query", {key: value for key, value in context.parameters.items() if key in keys}))
    if query.mode == "latest" and query.date_axis == "issue_id":
        query = replace(query, date_axis="issue_order")
    selection, report = select_publication_assets(listing, query, source_ids=(settings.source_id,))
    return {"selection": selection, "report": report}


def assess(inputs, settings, context):
    from stratbox.shared.data.materials import StagedMaterialRef
    from stratbox.shared.data.values import ImmutableMaterialRef
    materials = (Material, IdentifiedMaterial, ImmutableMaterialRef, StagedMaterialRef)
    evidence, baseline = inputs["evidence"], inputs.get("baseline")
    for value in (evidence, baseline):
        if isinstance(value, materials) and value.source_id not in {None, settings.source_id}:
            raise ValueError("rosstat.source_comparison_conflict")
    from stratbox.core.commands.publications import retained_validation_assessment
    retained = retained_validation_assessment(inputs, context)
    if retained is not None:
        return retained
    if isinstance(evidence, materials) and isinstance(baseline, materials):
        def coordinates(value):
            if isinstance(value, IdentifiedMaterial):
                return value.claim.source_id, value.claim.issue_id, value.claim.asset_id
            return value.source_id or settings.source_id, str(value.metadata.get("issue_id", "")), str(value.metadata.get("asset_id", "main"))
        before, after = coordinates(baseline), coordinates(evidence)
        if before != after:
            return {"assessment": UpdateAssessment("changed", "explicit_publication_coordinates",
                predecessor=fingerprint(before), candidate=fingerprint(after))}
    if isinstance(evidence, IdentifiedMaterial):
        evidence = evidence.material
    if isinstance(baseline, IdentifiedMaterial):
        baseline = baseline.material
    if isinstance(evidence, materials):
        candidate = evidence.identity.sha256
        previous = baseline.identity.sha256 if isinstance(baseline, materials) else None
        state = "first_seen" if baseline is None else "unknown" if previous is None else "unchanged" if previous == candidate else "changed"
        return {"assessment": UpdateAssessment(state, "exact_material_bytes", predecessor=previous, candidate=candidate)}
    if not isinstance(evidence, PublicationListing):
        raise TypeError("rosstat.source_evidence_required")
    if evidence.domain_id != "rosstat" or isinstance(baseline, PublicationListing) and baseline.domain_id != "rosstat":
        raise ValueError("rosstat.publication_listing_required")
    scope = context.parameters.get("comparison_scope", "selected")
    if scope not in {"selected", "feed"}:
        raise ValueError("rosstat.comparison_scope_invalid")
    def members(value):
        entries = value.entries
        if scope == "selected":
            from stratbox.shared.data.selection import select_publication_assets
            selected, _ = select_publication_assets(value, inputs.get("query"), source_ids=(settings.source_id,))
            entries = selected.entries
        return tuple(sorted((item.source_id, item.issue_id, item.asset_id, item.locator, item.format) for item in entries))
    candidate = fingerprint((scope, members(evidence)))
    previous = fingerprint((scope, members(baseline))) if isinstance(baseline, PublicationListing) else None
    # A partial index cannot establish disappearance or unchanged file bytes.
    # Reordering or relocation is evidence about the index, not a revision proof.
    status = "indeterminate"
    findings = (*evidence.assessment.findings, "publisher_inventory_or_material_bytes_not_established")
    return {"assessment": UpdateAssessment(status, "observed_index_scope", findings,
        predecessor=previous, candidate=candidate)}
