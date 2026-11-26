"""Fiscal attachment recognition over supplied evidence, without hidden I/O."""
from collections.abc import Mapping
from datetime import date
from urllib.parse import unquote, urljoin, urlsplit

from stratbox.shared.data.values import (
    Assessment, AssetSelection, Material, PublicationAsset, PublicationListing,
    RequestSpec, UpdateAssessment, fingerprint,
)
from ..common.access import ACCESS, allowed_url
from .cards import _Anchors, document_attachments


def _parameters(inputs, context):
    values = dict(getattr(context, "parameters", {}) or {})
    for name in ("locator", "query"):
        if isinstance(inputs.get(name), Mapping):
            values.update(inputs[name])
    return values


def prepare_request(inputs, settings, context):
    parameters = _parameters(inputs, context)
    selection = inputs.get("selection")
    locator = inputs.get("locator")
    role = parameters.get("role")
    if role is not None and role not in {"index", "asset"}:
        raise ValueError("minfin.request.role_invalid")
    if role == "index" and (isinstance(locator, PublicationAsset) or selection is not None):
        raise ValueError("minfin.request.index_asset_conflict")
    if isinstance(locator, PublicationAsset):
        if locator.source_id != settings.source_id:
            raise ValueError("minfin.request.source_mismatch")
        url = locator.locator
        metadata = {**locator.metadata, "issue_id": locator.issue_id, "asset_id": locator.asset_id}
        is_asset = True
    elif isinstance(selection, AssetSelection):
        if len(selection.entries) != 1 or selection.entries[0].source_id != settings.source_id:
            raise ValueError("minfin.request.single_matching_asset_required")
        asset = selection.entries[0]
        url, metadata = asset.locator, {**asset.metadata, "issue_id": asset.issue_id, "asset_id": asset.asset_id}
        is_asset = True
    else:
        url = parameters.get("url", settings.index_url)
        is_asset = role == "asset" or role != "index" and url != settings.index_url
        metadata = {key: parameters[key] for key in ("issue_id", "asset_id") if key in parameters}
    if not allowed_url(url, asset=is_asset):
        raise ValueError("minfin.request.url_forbidden")
    return {"request": RequestSpec(url, "GET",
        headers={"accept": "application/octet-stream,*/*" if is_asset else "text/html,application/xhtml+xml"},
        source_id=settings.source_id if is_asset else settings.family_id + ".index",
        max_bytes=ACCESS.asset_bytes if is_asset else ACCESS.index_bytes, metadata=metadata)}


def scan(inputs, settings, context):
    material = inputs["index"]
    if not isinstance(material, Material) or len(material.data) > ACCESS.index_bytes:
        raise ValueError("minfin.index.invalid")
    if material.source_id not in {None, settings.family_id + ".index", settings.source_id + ".index"}:
        raise ValueError("minfin.index.source_mismatch")
    html = material.data.decode(material.charset or "utf-8-sig")
    if "\x00" in html or "\ufffd" in html:
        raise ValueError("minfin.index.charset_invalid")
    parameters = _parameters(inputs, context)
    page_url = parameters.get("url", settings.index_url)
    anchors = _Anchors(2000)
    anchors.feed(html)
    anchors.close()
    if anchors.bad_base or anchors.overflow:
        raise ValueError("minfin.index.untrusted_or_oversized")
    if not anchors.links:
        raise ValueError("minfin.index.no_links")
    cards = {}
    for card in document_attachments(html):
        url = urljoin(page_url, card.href)
        if url in cards and cards[url] != card:
            raise ValueError("minfin.index.conflicting_document_evidence")
        cards[url] = card
    entries, findings = {}, []
    for href, label in anchors.links:
        url = urljoin(page_url, href)
        if not allowed_url(url, asset=True):
            continue
        filename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        fmt = filename.rsplit(".", 1)[-1].casefold()
        card = cards.get(url)
        documented = [rule for rule in settings.siblings if card and card.document_id == rule.document_id]
        named = [rule for rule in settings.siblings if filename.casefold().startswith(rule.prefix.casefold())
                 and filename.casefold().endswith(rule.suffix.casefold())]
        if len(documented) > 1 or len(named) > 1 or documented and named and documented[0] != named[0]:
            findings.append("minfin.asset.conflicting_identity:" + filename)
            continue
        rule = documented[0] if documented else named[0] if named else None
        if rule is None:
            findings.append("minfin.asset.unclassified:" + filename)
            continue
        if fmt != rule.format:
            findings.append("minfin.asset.format_conflict:" + filename)
            continue
        marker = card.modified_on or card.published_on if card else None
        issue_id = marker.isoformat() if marker else rule.document_id
        metadata = {"filename": filename, "document_id": rule.document_id,
                    "modified_on": card.modified_on.isoformat() if card and card.modified_on else None,
                    "published_on": card.published_on.isoformat() if card and card.published_on else None,
                    "publication_date": card.published_on.isoformat() if card and card.published_on else None,
                    "label": card.document_title if card else label,
                    "index_identity": material.identity.sha256}
        entries[url] = PublicationAsset(rule.source_id, issue_id, rule.asset_id, url, fmt, metadata)
    if not entries:
        findings.append("minfin.asset.none_in_observed_scope")
    assessment = Assessment("partial" if findings else "complete", tuple(findings),
        observed=tuple(sorted(item.source_id for item in entries.values())),
        qualifications=frozenset({"source.observed_index_page_only"}))
    return {"listing": PublicationListing("minfin", tuple(sorted(entries.values(),
        key=lambda item: (item.source_id, item.issue_id, item.locator))), assessment, (material.identity,)),
        "coverage": assessment}


def select(inputs, settings, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing) or listing.domain_id != "minfin":
        raise ValueError("minfin.publication_listing_required")
    from stratbox.shared.data.selection import IssueQuery, select_publication_assets
    keys = set(IssueQuery.__dataclass_fields__) | {"source_id", "asset_id", "issue_id", "issue", "as_of", "periods", "format", "locator", "url"}
    query = inputs.get("query", {key: value for key, value in _parameters(inputs, context).items() if key in keys})
    selection, report = select_publication_assets(listing, query, source_ids=(settings.source_id,))
    return {"selection": selection, "report": report}


def assess(inputs, settings, context):
    from stratbox.shared.data.materials import StagedMaterialRef
    from stratbox.shared.data.values import IdentifiedMaterial, ImmutableMaterialRef
    materials = (Material, IdentifiedMaterial, ImmutableMaterialRef, StagedMaterialRef)
    evidence = inputs["evidence"]
    baseline = inputs.get("baseline")
    for value in (evidence, baseline):
        source = getattr(value, "source_id", None)
        if source is not None and source not in {settings.source_id, settings.source_id + ".index", settings.family_id + ".index"}:
            raise ValueError("minfin.source_comparison_conflict")
    from stratbox.core.commands.publications import retained_validation_assessment
    retained = retained_validation_assessment(inputs, context)
    if retained is not None:
        return retained
    if isinstance(evidence, PublicationListing):
        if evidence.domain_id != "minfin" or isinstance(baseline, PublicationListing) and baseline.domain_id != "minfin":
            raise ValueError("minfin.publication_listing_required")
        scope = context.parameters.get("comparison_scope", "selected")
        if scope not in {"selected", "feed"}:
            raise ValueError("minfin.comparison_scope_invalid")
        def members(value):
            entries = value.entries
            assessment = value.assessment
            if scope == "selected":
                from stratbox.shared.data.selection import select_publication_assets
                selected, report = select_publication_assets(value, inputs.get("query"), source_ids=(settings.source_id,))
                entries = selected.entries
                assessment = report.assessment
            return tuple(sorted((item.source_id, item.issue_id, item.asset_id, item.locator, item.format) for item in entries)), assessment
        selected, coverage = members(evidence)
        previous, previous_coverage = members(baseline) if isinstance(baseline, PublicationListing) else (None, None)
        candidate = fingerprint((scope, selected))
        prior = fingerprint((scope, previous)) if previous is not None else None
        status = "first_seen" if prior is None else "unknown" if prior == candidate else "changed"
        if not coverage.complete or previous_coverage is not None and not previous_coverage.complete:
            status = "unknown"
        return {"assessment": UpdateAssessment(status, "observed_publication_listing",
            ("minfin.index_does_not_establish_asset_bytes",), predecessor=prior, candidate=candidate,
            evidence={"scope": scope, "source_id": settings.source_id, "source_coverage": evidence.assessment,
                "selected_coverage": coverage, "previous_selected_coverage": previous_coverage})}
    if isinstance(evidence, materials):
        def coordinates(value):
            if isinstance(value, IdentifiedMaterial):
                return value.claim.source_id, value.claim.issue_id, value.claim.asset_id
            return value.source_id or settings.source_id, str(value.metadata.get("issue_id", "")), str(value.metadata.get("asset_id", "main"))
        candidate = evidence.identity.sha256
        previous = baseline.identity.sha256 if isinstance(baseline, materials) else None
        if isinstance(baseline, materials) and coordinates(evidence) != coordinates(baseline):
            return {"assessment": UpdateAssessment("changed", "explicit_publication_coordinates",
                predecessor=fingerprint(coordinates(baseline)), candidate=fingerprint(coordinates(evidence)))}
        status = "first_seen" if baseline is None else "unknown" if previous is None else "unchanged" if previous == candidate else "changed"
        return {"assessment": UpdateAssessment(status, "exact_material_bytes", predecessor=previous, candidate=candidate)}
    candidate = fingerprint(evidence)
    prior = baseline.candidate if isinstance(baseline, UpdateAssessment) else fingerprint(baseline) if baseline is not None else None
    status = "new_issue" if prior is None else "unchanged" if prior == candidate else "changed"
    if not getattr(evidence, "assessment", Assessment()).complete:
        status = "indeterminate"
    return {"assessment": UpdateAssessment(status, "qualified_publication_evidence", predecessor=prior, candidate=candidate)}
