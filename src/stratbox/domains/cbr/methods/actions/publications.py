"""Pure publisher request preparation, inventory interpretation and attribution."""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin, urlsplit

from stratbox.shared.data.values import (
    Assessment, AssetSelection, IdentifiedMaterial, Material, PublicationAsset,
    PublicationListing, RequestSpec, SourceClaim, UpdateAssessment, fingerprint,
    WorkbookEvidence, TableEvidenceSet, SourceDataset,
    FetchEvidence, request_identity,
)
from stratbox.domains.cbr.common.access import CBR_ACCESS


def _parameters(context):
    return getattr(context, "parameters", {})


def _date(value):
    if type(value) is date:
        return value.isoformat()
    token = str(value or "")
    if re.fullmatch(r"\d{8}", token):
        token = f"{token[:4]}-{token[4:6]}-{token[6:]}"
    try:
        return date.fromisoformat(token).isoformat()
    except ValueError:
        return None


def _allowed(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in CBR_ACCESS.hosts
            or parts.username or parts.password or parts.fragment
            or parts.port not in (None, 443)
            or not parts.path.lower().startswith(CBR_ACCESS.source_roots)):
        raise ValueError("cbr.source_url_invalid")
    return url


def prepare_request(inputs, settings, context):
    locator = inputs.get("locator")
    query = inputs.get("query") or _parameters(context)
    selection = inputs.get("selection")
    if selection is not None:
        if (not isinstance(selection, AssetSelection) or not selection.assessment.complete
                or len(selection.entries) != 1):
            raise ValueError("cbr.request_single_qualified_asset_required")
        if locator is not None and locator != selection.entries[0]:
            raise ValueError("cbr.request_asset_mismatch")
        locator = selection.entries[0]
    if "locator" in inputs and (locator is None or isinstance(locator, str) and not locator.strip()):
        raise ValueError("cbr.source_url_invalid")
    if isinstance(locator, PublicationAsset):
        if (locator.source_id != settings.series_id or locator.format not in settings.formats
                or query.get("issue_id") is not None and str(query["issue_id"]) != locator.issue_id):
            raise ValueError("cbr.request_asset_mismatch")
    url = locator.locator if isinstance(locator, PublicationAsset) else locator or settings.locator
    if settings.family_id == "cbr.reporting_forms" and query.get("issue_id") and locator is None:
        issued = _date(query["issue_id"])
        if issued is None:
            raise ValueError("cbr.issue_date_invalid")
        code = settings.series_id.rsplit(".f", 1)[1]
        fmt = query.get("format", "rar")
        if fmt not in settings.formats:
            raise ValueError("cbr.source_format_unavailable")
        url = f"https://www.cbr.ru/vfs/credit/forms/{code}-{issued.replace('-', '')}.{fmt}"
    request = RequestSpec(_allowed(str(url)), max_bytes=CBR_ACCESS.max_response_bytes,
        timeout=CBR_ACCESS.deadline_seconds, source_id=settings.series_id,
        headers={"accept": "application/octet-stream,text/html,*/*"}, metadata={
            "issue_id": locator.issue_id if isinstance(locator, PublicationAsset) else str(query.get("issue_id", "")),
            "asset_id": locator.asset_id if isinstance(locator, PublicationAsset) else "main"})
    return {"request": request}


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag.casefold() == "a":
            self.current = (dict(attrs).get("href"), [])

    def handle_data(self, text):
        if self.current is not None:
            self.current[1].append(text)

    def handle_endtag(self, tag):
        if tag.casefold() == "a" and self.current is not None:
            href, parts = self.current
            if href:
                self.links.append((href, " ".join(parts)))
            self.current = None


def scan(inputs, settings, context):
    supplied = inputs.get("index")
    if isinstance(supplied, IdentifiedMaterial):
        if supplied.source_id not in {settings.series_id, settings.series_id + ".index"}:
            raise ValueError("cbr.index_source_mismatch")
        supplied = supplied.material
    if not isinstance(supplied, Material):
        raise ValueError("cbr.supplied_index_required")
    if supplied.source_id not in {None, settings.series_id, settings.series_id + ".index"}:
        raise ValueError("cbr.index_source_mismatch")
    if settings.kind in {"fixed", "page"}:
        entries = (PublicationAsset(settings.series_id, "", "main", settings.locator,
            "html" if settings.kind == "page" else PurePosixPath(urlsplit(settings.locator).path).suffix.lstrip(".")),)
    else:
        parser = _Links()
        parser.feed(supplied.data.decode(supplied.charset or "utf-8"))
        entries = []
        seen = set()
        limit = int(_parameters(context).get("max_links", 10000))
        if limit < 1:
            raise ValueError("cbr.link_limit_invalid")
        if len(parser.links) > limit:
            raise ValueError("cbr.index_link_limit")
        for href, label in parser.links:
            context.checkpoint()
            try:
                url = urljoin(settings.locator, href)
                _allowed(url)
            except ValueError:
                continue
            path = urlsplit(url).path
            fmt = PurePosixPath(path).suffix.lstrip(".").lower()
            issue = None
            if settings.filename_pattern:
                match = re.search(settings.filename_pattern, path, re.I)
                if match is None:
                    continue
                token = match.groupdict().get("date")
                issue = _date(token)
                # Dated statistical workbooks use DDMMYYYY in the file name.
                if issue is None and token and len(token) == 8:
                    issue = _date(token[4:] + token[2:4] + token[:2])
            elif settings.kind == "escrow_index":
                if fmt == "xlsx":
                    match = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)", path)
                    if match:
                        issue = _date(match[3] + match[2] + match[1])
                else:
                    match = re.search(r"/finansirovanie-dolevogo-stroitelstva/(\d{4}-\d{2}-\d{2})/?$", path)
                    if match is None:
                        continue
                    fmt, issue = "html", _date(match[1])
            if fmt not in settings.formats or settings.filename_pattern and issue is None:
                continue
            key = (issue, url)
            if key in seen:
                continue
            seen.add(key)
            entries.append(PublicationAsset(settings.series_id, issue or "", "main", url, fmt,
                {"publisher_label": label, "issue_qualification": "dated" if issue else "unresolved"}))
        entries = tuple(entries)
    assessment = Assessment("complete" if entries else "partial",
        () if entries else ("cbr.index_no_qualified_assets",),
        qualifications=frozenset({"observed_index_only"}))
    return {"listing": PublicationListing("cbr", tuple(entries), assessment, (supplied.identity,)),
            "coverage": assessment}


def select(inputs, settings, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing):
        raise ValueError("cbr.publication_listing_required")
    query = inputs.get("query") or _parameters(context)
    issue = query.get("issue_id")
    requested_format = query.get("format")
    requested_locator = query.get("locator")
    entries = tuple(entry for entry in listing.entries if entry.source_id == settings.series_id
        and (issue is None or entry.issue_id == str(issue))
        and (requested_format is None or entry.format == requested_format)
        and (requested_locator is None or entry.locator == str(requested_locator)))
    conflicts = len({entry.locator for entry in entries}) > 1 and len({entry.issue_id for entry in entries}) == 1
    status = "conflicted" if conflicts or listing.assessment.status == "conflicted" else "complete" if entries and listing.assessment.complete else "partial"
    findings = ("cbr.asset_selection_ambiguous",) if conflicts else () if entries else ("cbr.asset_selection_empty",)
    assessment = Assessment(status, (*listing.assessment.findings, *findings), qualifications=listing.assessment.qualifications)
    return {"selection": AssetSelection(entries, assessment)}


def assess(inputs, settings, context):
    evidence, baseline = inputs.get("evidence"), inputs.get("baseline")
    def coordinates(value):
        return value.claim.source_id, value.claim.issue_id, value.claim.asset_id
    for value in (evidence, baseline):
        if isinstance(value, (Material, IdentifiedMaterial)) and value.source_id not in {None, settings.series_id}:
            raise ValueError("cbr.source_assessment_source_mismatch")
    if isinstance(evidence, PublicationListing) and not evidence.assessment.complete:
        result = UpdateAssessment("unknown", "publication_listing_incomplete", evidence.assessment.findings,
            candidate=fingerprint(evidence), evidence=evidence.assessment)
    elif baseline is None:
        result = UpdateAssessment("first_seen", "no_baseline", candidate=fingerprint(evidence))
    elif isinstance(evidence, (WorkbookEvidence, TableEvidenceSet)) and isinstance(baseline, type(evidence)):
        from stratbox.domains.cbr.methods.actions.workbook_comparison import compare_workbooks
        comparison = compare_workbooks(baseline, evidence, checkpoint=context.checkpoint)
        result = UpdateAssessment(comparison.source_change, "physical_workbook_evidence",
            (comparison.issue_change,), comparison.before.sha256, comparison.after.sha256, comparison)
    elif isinstance(evidence, SourceDataset) and isinstance(baseline, SourceDataset):
        if evidence.source_id != baseline.source_id:
            raise ValueError("cbr.dataset_comparison_source_mismatch")
        def facts(value):
            return tuple({key: field for key, field in row.items() if key not in {"raw_token", "evidence_ref"}}
                for row in value.rows)
        same = facts(evidence) == facts(baseline)
        result = UpdateAssessment("facts_changed" if not same else "unchanged" if evidence.identity == baseline.identity else "representation_changed",
            "interpreted_source_observations", predecessor=baseline.identity, candidate=evidence.identity)
    elif isinstance(evidence, IdentifiedMaterial) and isinstance(baseline, IdentifiedMaterial) and coordinates(evidence) != coordinates(baseline):
        result = UpdateAssessment("changed", "explicit_publication_coordinates",
            ("cbr.same_bytes_do_not_erase_distinct_publication_coordinates",),
            fingerprint(coordinates(baseline)), fingerprint(coordinates(evidence)))
    elif isinstance(evidence, (Material, IdentifiedMaterial)) and isinstance(baseline, type(evidence)):
        result = UpdateAssessment("unchanged" if evidence.identity == baseline.identity else "changed",
            "exact_material_bytes", predecessor=baseline.identity.sha256, candidate=evidence.identity.sha256)
    elif isinstance(evidence, PublicationListing) and isinstance(baseline, PublicationListing):
        old = {(v.source_id, v.issue_id, v.asset_id, v.locator) for v in baseline.entries}
        new = {(v.source_id, v.issue_id, v.asset_id, v.locator) for v in evidence.entries}
        result = UpdateAssessment("changed" if old != new else "unknown", "observed_publication_listing",
            () if old != new else ("cbr.unchanged_index_does_not_certify_asset_bytes",),
            fingerprint(baseline), fingerprint(evidence))
    else:
        result = UpdateAssessment("unknown", "insufficient_comparable_evidence")
    return {"assessment": result}


def identify(inputs, settings, context):
    value = inputs["material"]
    asset, request, fetch = inputs.get("asset"), inputs.get("request"), inputs.get("evidence")
    if asset is not None and (not isinstance(asset, PublicationAsset) or asset.source_id != settings.series_id or asset.format not in settings.formats):
        raise ValueError("cbr.material_asset_mismatch")
    issue = asset.issue_id if asset is not None else str(_parameters(context).get("issue_id", ""))
    verified = (isinstance(value, Material) and isinstance(request, RequestSpec) and isinstance(fetch, FetchEvidence)
        and request.source_id == settings.series_id and fetch.request_identity == request_identity(request)
        and fetch.material_identity == value.identity and 200 <= fetch.status_code < 300)
    if request is not None:
        if not isinstance(request, RequestSpec) or request.source_id != settings.series_id:
            raise ValueError("cbr.material_request_mismatch")
        _allowed(request.url)
        if asset is not None and request.url != asset.locator:
            raise ValueError("cbr.material_asset_mismatch")
    claim = inputs.get("claim") or SourceClaim(settings.series_id, issue,
        asset.asset_id if asset is not None else "main", "verified" if verified else "asserted")
    if not isinstance(value, Material) or not isinstance(claim, SourceClaim):
        raise ValueError("cbr.material_claim_required")
    if value.source_id not in {None, settings.series_id} or claim.source_id != settings.series_id:
        raise ValueError("cbr.material_source_mismatch")
    if claim.issue_id or settings.issue_required:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", claim.issue_id) or _date(claim.issue_id) != claim.issue_id:
            raise ValueError("cbr.issue_date_invalid")
    if asset is not None and (asset.issue_id and claim.issue_id != asset.issue_id or claim.asset_id != asset.asset_id):
        raise ValueError("cbr.material_asset_mismatch")
    if claim.attribution == "verified" and not verified:
        raise ValueError("cbr.verified_attribution_requires_evidence")
    media = value.media_type.partition(";")[0].strip().lower()
    data = value.data
    if data.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        detected = "rar"
    elif data.startswith(b"PK\x03\x04"):
        detected = "zip"
    elif data.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
        detected = "html"
    else:
        detected = None
    if len(data) >= 32 and data[0] in {0x02, 0x03, 0x04, 0x05, 0x30, 0x31, 0x32, 0x43, 0x63, 0x83, 0x8B, 0xCB, 0xF5}:
        detected = "dbf"
    declared = {"application/rar": "rar", "application/x-rar": "rar", "application/x-rar-compressed": "rar",
        "application/zip": "zip", "application/x-zip-compressed": "zip", "text/html": "html",
        "application/xhtml+xml": "html", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "zip",
        "application/vnd.ms-excel": "xls"}.get(media)
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        detected = "xls"
    if declared is not None and detected != declared:
        raise ValueError("cbr.material_media_signature_mismatch")
    if detected is None:
        raise ValueError("cbr.material_format_signature_required")
    if detected == "zip":
        from io import BytesIO
        from zipfile import BadZipFile, ZipFile
        try:
            with ZipFile(BytesIO(data)) as archive:
                names = set(archive.namelist())
                if "zip" not in settings.formats and not {"[Content_Types].xml", "xl/workbook.xml"} <= names:
                    raise ValueError("cbr.material_workbook_envelope_required")
        except BadZipFile as error:
            raise ValueError("cbr.material_archive_envelope_invalid") from error
    if detected == "rar" and "rar" not in settings.formats or detected == "html" and "html" not in settings.formats:
        raise ValueError("cbr.material_format_unavailable")
    assessment = Assessment("complete", qualifications=frozenset({"source_bound" if value.source_id else "caller_asserted_source"}))
    return {"material": IdentifiedMaterial(value, claim, assessment), "assessment": assessment}
