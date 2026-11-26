"""Pure FNS publication procedures; request execution is a core action."""
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

from stratbox.shared.data.values import (
    Assessment, AssetSelection, Material, PublicationAsset, PublicationListing,
    RequestSpec, UpdateAssessment, fingerprint,
)
from ..common.access import ACCESS


def _query(inputs, context):
    parameters = dict(getattr(context, "parameters", {}) or {})
    query = inputs.get("query", inputs.get("locator", {}))
    if isinstance(query, dict) or hasattr(query, "items"):
        parameters.update(query)
    elif query is not None:
        from stratbox.shared.data.selection import IssueQuery
        if isinstance(query, IssueQuery):
            if len(query.issues) == 1:
                parameters["issue_id"] = query.issues[0]
            elif query.issues:
                raise ValueError("fns.request.single_issue_required")
    return parameters


def parse_day(value):
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value[:10], "%d.%m.%Y").date()
            except ValueError:
                pass
    raise ValueError("fns.publication.date_required")


def prepare_request(inputs, settings, context):
    query = _query(inputs, context)
    selection = inputs.get("selection")
    locator = inputs.get("locator")
    if isinstance(locator, PublicationAsset):
        if locator.source_id != settings.source_id:
            raise ValueError("fns.request.source_mismatch")
        query.update(url=locator.locator, issue_id=locator.issue_id)
    if isinstance(selection, AssetSelection):
        if len(selection.entries) != 1:
            raise ValueError("fns.request.single_asset_required")
        asset = selection.entries[0]
        if asset.source_id != settings.source_id:
            raise ValueError("fns.request.source_mismatch")
        query.update(url=asset.locator, issue_id=asset.issue_id)
    reference = query.get("as_of", query.get("issue_id", query.get("date")))
    role = query.get("role", "asset" if reference is not None or selection or isinstance(locator, PublicationAsset) else "index")
    if role not in {"index", "asset"}:
        raise ValueError("fns.request.role_invalid")
    if role == "index":
        if isinstance(locator, PublicationAsset) or selection is not None:
            raise ValueError("fns.request.index_asset_conflict")
        url = query.get("url", settings.index_url)
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.hostname not in ACCESS.hosts
                or parts.username or parts.password or parts.fragment or parts.port not in {None, 443}):
            raise ValueError("fns.request.host_invalid")
        return {"request": RequestSpec(url, max_bytes=ACCESS.max_index_bytes,
            source_id=settings.source_id + ".index")}
    day = parse_day(reference)
    if day < settings.earliest or day > date(2099, 12, 31) or settings.first_day and day.day != 1:
        raise ValueError("fns.request.date_invalid")
    url = settings.data_url or query.get("url")
    if not isinstance(url, str):
        raise ValueError("fns.request.asset_url_required")
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in ACCESS.hosts
            or parts.username or parts.password or parts.fragment or parts.port not in {None, 443}):
        raise ValueError("fns.request.asset_url_required")
    form = {"statDate": day.strftime("%d.%m.%Y")} if settings.method == "POST" else None
    return {"request": RequestSpec(url, settings.method,
        headers={"accept": "application/json"} if form else {}, form=form,
        source_id=settings.source_id, max_bytes=settings.max_bytes,
        read_only=True, metadata={"issue_id": day.isoformat(), "as_of": day.isoformat()})}


class _Dates(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = set()

    def handle_starttag(self, tag, attrs):
        if tag.casefold() == "option":
            value = dict(attrs).get("value", "")
            if re.fullmatch(r"\d{2}\.\d{2}\.20\d{2}", value):
                self.days.add(parse_day(value))


class _LegalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.labels, self.links, self.items = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            if not self.depth:
                self.labels, self.links = [], []
            self.depth += 1
        if tag == "a" and self.depth:
            self.links.append(dict(attrs).get("href", ""))

    def handle_data(self, data):
        if self.depth:
            self.labels.append(data)

    def handle_endtag(self, tag):
        if tag == "li" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.items.append((" ".join(self.labels), tuple(self.links)))


def scan_sme(inputs, settings, context):
    material = inputs["index"]
    if not isinstance(material, Material):
        raise TypeError("fns.index.material_required")
    if material.source_id not in {None, settings.source_id + ".index"}:
        raise ValueError("fns.index.source_mismatch")
    parser = _Dates()
    parser.feed(material.data.decode(material.charset or "utf-8-sig"))
    entries = tuple(PublicationAsset(settings.source_id, day.isoformat(), "statistics",
        settings.data_url, "json", {"as_of": day.isoformat(), "reporting_date": day.isoformat(),
            "measurement_date": day.isoformat()}) for day in sorted(parser.days)
        if day >= settings.earliest)
    if not entries:
        raise ValueError("fns.sme.publication_dates_unavailable")
    assessment = Assessment("complete", observed=tuple(item.issue_id for item in entries),
        qualifications=frozenset({"source.observed_index_dates_only"}))
    return {"listing": PublicationListing("fns", entries, assessment, (material.identity,)),
            "coverage": assessment}


def scan_legal(inputs, settings, context):
    material = inputs["index"]
    if not isinstance(material, Material) or material.source_id not in {None, settings.source_id + ".index"}:
        raise ValueError("fns.index.source_mismatch")
    parser = _LegalLinks()
    parser.feed(material.data.decode(material.charset or "utf-8-sig"))
    query = _query(inputs, context)
    page_url = query.get("url", settings.index_url)
    found, missing = {}, []
    for label, links in parser.items:
        if "регистрации юридических лиц" not in label.casefold():
            continue
        tokens = re.findall(r"(?<!\d)\d{2}\.\d{2}\.20\d{2}(?!\d)", label)
        if len(tokens) != 1:
            continue
        day = parse_day(tokens[0])
        if day < settings.earliest or day.day != 1:
            continue
        candidates = set()
        for link in links:
            url = urljoin(page_url, link)
            parts = urlsplit(url)
            if parts.scheme == "https" and parts.hostname in ACCESS.hosts and parts.path.casefold().endswith((".xls", ".xlsx", ".zip", ".rar")):
                candidates.add(url)
        if not candidates:
            missing.append(day.isoformat())
            continue
        if len(candidates) != 1:
            raise ValueError("fns.1yur.asset_ambiguous")
        url = next(iter(candidates))
        if day in found and found[day] != url:
            raise ValueError("fns.1yur.duplicate_issue")
        found[day] = url
    entries = tuple(PublicationAsset(settings.source_id, day.isoformat(), "main", url,
        urlsplit(url).path.rsplit(".", 1)[-1].casefold(), {"as_of": day.isoformat(), "reporting_date": day.isoformat()})
        for day, url in sorted(found.items()))
    findings = tuple("fns.1yur.asset_missing:" + value for value in sorted(set(missing)))
    if not entries:
        findings += ("fns.1yur.no_assets_in_observed_scope",)
    assessment = Assessment("partial" if findings else "complete", findings,
        observed=tuple(item.issue_id for item in entries),
        qualifications=frozenset({"source.observed_index_page_only"}))
    return {"listing": PublicationListing("fns", entries, assessment, (material.identity,)),
            "coverage": assessment}


def select_issue(inputs, settings, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing) or listing.domain_id != "fns":
        raise ValueError("fns.publication_listing_required")
    from stratbox.shared.data.selection import IssueQuery, select_publication_assets
    keys = set(IssueQuery.__dataclass_fields__) | {"source_id", "asset_id", "issue_id", "issue", "as_of", "periods", "format", "locator", "url"}
    query = inputs.get("query", {key: value for key, value in _query(inputs, context).items() if key in keys})
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
        if source is not None and source not in {settings.source_id, settings.source_id + ".index"}:
            raise ValueError("fns.source_comparison_conflict")
    from stratbox.core.commands.publications import retained_validation_assessment
    retained = retained_validation_assessment(inputs, context)
    if retained is not None:
        return retained
    if isinstance(evidence, PublicationListing):
        if evidence.domain_id != "fns" or isinstance(baseline, PublicationListing) and baseline.domain_id != "fns":
            raise ValueError("fns.publication_listing_required")
        scope = context.parameters.get("comparison_scope", "selected")
        if scope not in {"selected", "feed"}:
            raise ValueError("fns.comparison_scope_invalid")
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
            ("fns.index_does_not_establish_asset_bytes",), predecessor=prior, candidate=candidate,
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
    if baseline is None:
        status, predecessor = "new_issue", None
    elif isinstance(baseline, UpdateAssessment):
        predecessor = baseline.candidate
        status = "unchanged" if predecessor == candidate else "changed"
    else:
        predecessor = fingerprint(baseline)
        status = "unchanged" if predecessor == candidate else "changed"
    assessment = getattr(evidence, "assessment", Assessment())
    if not assessment.complete:
        status = "indeterminate"
    return {"assessment": UpdateAssessment(status, "qualified_publication_evidence",
        predecessor=predecessor, candidate=candidate)}
