"""Pure publisher request preparation, inventory interpretation and attribution."""
from __future__ import annotations

from datetime import date
from collections.abc import Mapping
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


def _query(inputs, context):
    parameters = dict(_parameters(context))
    query = inputs.get("query")
    if isinstance(query, Mapping):
        parameters.update(query)
    elif query is not None:
        from stratbox.shared.data.selection import IssueQuery
        if not isinstance(query, IssueQuery):
            raise ValueError("cbr.publication_query_invalid")
        if len(query.issues) == 1:
            parameters["issue_id"] = query.issues[0]
        if query.formats:
            parameters["format"] = query.formats[0]
    return parameters


def _asset_matches(asset, settings):
    if asset.source_id == settings.series_id:
        return True
    return (getattr(settings, "feed_id", None) == asset.source_id
        and getattr(settings, "feed_asset_id", None) == asset.asset_id)


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


def _escrow_issue(path, fmt):
    if fmt == "xlsx":
        match = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)", path)
        return _date(match[3] + match[2] + match[1]) if match else None
    match = re.search(r"/finansirovanie-dolevogo-stroitelstva/(\d{4}-\d{2}-\d{2})/?$", path)
    return _date(match[1]) if match else None


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
    query = _query(inputs, context)
    role = query.get("role", "asset" if locator is not None or inputs.get("selection") is not None
        or query.get("issue_id") or settings.kind in {"fixed", "page"} else "index")
    if role not in {"index", "asset"}:
        raise ValueError("cbr.request_role_invalid")
    if role == "index":
        if isinstance(locator, PublicationAsset):
            raise ValueError("cbr.index_asset_conflict")
        return {"request": RequestSpec(_allowed(settings.locator), max_bytes=CBR_ACCESS.max_response_bytes,
            timeout=CBR_ACCESS.deadline_seconds, source_id=settings.series_id + ".index",
            headers={"accept": "text/html,application/octet-stream,*/*"},
            metadata={"asset_id": "index", "role": "index"})}
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
        if (not _asset_matches(locator, settings) or locator.format not in settings.formats
                or query.get("issue_id") is not None and str(query["issue_id"]) != locator.issue_id):
            raise ValueError("cbr.request_asset_mismatch")
    url = locator.locator if isinstance(locator, PublicationAsset) else locator or settings.locator
    if settings.family_id == "cbr.reporting_forms" and query.get("issue_id") and locator is None:
        issued = _date(query["issue_id"])
        if issued is None:
            raise ValueError("cbr.issue_date_invalid")
        if settings.kind == "forms_index":
            code = str(query.get("form_code", ""))
            if not re.fullmatch(r"\d{3}", code):
                raise ValueError("cbr.explicit_form_code_required")
        else:
            code = settings.series_id.rsplit(".f", 1)[1]
        fmt = query.get("format", "rar")
        if fmt not in settings.formats:
            raise ValueError("cbr.source_format_unavailable")
        url = f"https://www.cbr.ru/vfs/credit/forms/{code}-{issued.replace('-', '')}.{fmt}"
    request = RequestSpec(_allowed(str(url)), max_bytes=CBR_ACCESS.max_response_bytes,
        timeout=CBR_ACCESS.deadline_seconds, source_id=locator.source_id if isinstance(locator, PublicationAsset) else settings.series_id,
        headers={"accept": "application/octet-stream,text/html,*/*"}, metadata={
            "issue_id": locator.issue_id if isinstance(locator, PublicationAsset) else str(query.get("issue_id", "")),
            "asset_id": locator.asset_id if isinstance(locator, PublicationAsset) else (
                "form-0409" + code if settings.kind == "forms_index" and query.get("issue_id") else "main"),
            "role": "asset", "discovery": "observed_index" if isinstance(locator, PublicationAsset)
                and locator.metadata.get("discovery") == "observed_index" else "explicit_locator"})
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
                match = (re.fullmatch(settings.filename_pattern, PurePosixPath(path).name, re.I)
                    if settings.kind == "forms_index" else re.search(settings.filename_pattern, path, re.I))
                if match is None:
                    continue
                token = match.groupdict().get("date")
                issue = _date(token)
                # Dated statistical workbooks use DDMMYYYY in the file name.
                if issue is None and token and len(token) == 8:
                    issue = _date(token[4:] + token[2:4] + token[:2])
            elif settings.kind == "escrow_index":
                issue = _escrow_issue(path, fmt)
                if issue is None:
                    continue
                if fmt != "xlsx":
                    fmt = "html"
            if fmt not in settings.formats or settings.filename_pattern and issue is None:
                continue
            key = (issue, url)
            if key in seen:
                continue
            seen.add(key)
            metadata = {"publisher_label": label, "issue_qualification": "dated" if issue else "unresolved",
                "discovery": "observed_index", "index_identity": supplied.identity.sha256}
            if issue is not None and settings.filename_pattern:
                metadata["filename_date"] = issue
                if settings.family_id in {"cbr.reporting_forms", "cbr.corporate_lending"}:
                    metadata["reporting_date"] = issue
            asset_id = "main"
            if settings.kind == "forms_index":
                code = match.group("form")
                asset_id = "form-0409" + code
                metadata.update(form_code=code, publisher_form_code="0409" + code, role="regulatory_archive")
                known_series = dict(settings.memberships).get(asset_id)
                if known_series is not None:
                    metadata["known_series_id"] = known_series
            entries.append(PublicationAsset(settings.series_id, issue or "", asset_id, url, fmt, metadata))
        entries = tuple(entries)
    assessment = Assessment("complete" if entries else "partial",
        () if entries else ("cbr.index_no_qualified_assets",),
        qualifications=frozenset({"observed_index_only"}))
    return {"listing": PublicationListing("cbr", tuple(entries), assessment, (supplied.identity,)),
            "coverage": assessment}


def select(inputs, settings, context):
    listing = inputs["listing"]
    if not isinstance(listing, PublicationListing) or listing.domain_id != "cbr":
        raise ValueError("cbr.publication_listing_required")
    from stratbox.shared.data.selection import IssueQuery, select_publication_assets
    keys = set(IssueQuery.__dataclass_fields__) | {"source_id", "asset_id", "issue_id", "issue", "as_of", "periods", "format", "locator", "url"}
    query = inputs.get("query", {key: value for key, value in _parameters(context).items() if key in keys})
    if settings.kind == "forms_index" and not query:
        raise ValueError("cbr.explicit_form_selection_required")
    selection, report = select_publication_assets(listing, query, source_ids=(settings.series_id,))
    return {"selection": selection, "report": report}


def assess(inputs, settings, context):
    from stratbox.shared.data.materials import StagedMaterialRef
    from stratbox.shared.data.values import ImmutableMaterialRef
    materials = (Material, IdentifiedMaterial, ImmutableMaterialRef, StagedMaterialRef)
    evidence, baseline = inputs.get("evidence"), inputs.get("baseline")
    if isinstance(evidence, PublicationListing):
        if evidence.domain_id != "cbr" or isinstance(baseline, PublicationListing) and baseline.domain_id != "cbr":
            raise ValueError("cbr.publication_listing_required")
        scope = _parameters(context).get("comparison_scope", "selected")
        if scope not in {"selected", "feed"}:
            raise ValueError("cbr.comparison_scope_invalid")
        def members(value):
            entries = value.entries
            assessment = value.assessment
            if scope == "selected":
                from stratbox.shared.data.selection import select_publication_assets
                selection, report = select_publication_assets(value, inputs.get("query"), source_ids=(settings.series_id,))
                entries = selection.entries
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
            ("cbr.unchanged_index_does_not_certify_asset_bytes",) if prior == candidate else (),
            predecessor=prior, candidate=candidate,
            evidence={"scope": scope, "source_id": settings.series_id, "source_coverage": evidence.assessment,
                "selected_coverage": coverage, "previous_selected_coverage": previous_coverage})}
    def coordinates(value):
        if value.source_id not in {None, settings.series_id}:
            verify = getattr(context, "verify_source_use", None)
            relation = next((use.coordinate for use in getattr(value, "source_uses", ())
                if use.coordinate.source_id == value.source_id == getattr(settings, "feed_id", None)
                and use.coordinate.asset_id == getattr(settings, "feed_asset_id", None)
                and use.coordinate.material_identity == value.identity
                and use.input_role == "publication_acquisition" and verify is not None and verify(use)), None)
            if relation is None:
                raise ValueError("cbr.source_assessment_source_mismatch")
            return settings.series_id, relation.issue_id or "", relation.asset_id or "main"
        if isinstance(value, IdentifiedMaterial):
            return value.claim.source_id, value.claim.issue_id, value.claim.asset_id
        return value.source_id or settings.series_id, str(value.metadata.get("issue_id", "")), str(value.metadata.get("asset_id", "main"))
    for value in (evidence, baseline):
        if isinstance(value, materials):
            coordinates(value)
        elif isinstance(value, (TableEvidenceSet, SourceDataset)) and value.source_id not in {None, settings.series_id}:
            raise ValueError("cbr.source_assessment_source_mismatch")
        elif isinstance(value, WorkbookEvidence):
            coordinates(value.material)
    from stratbox.core.commands.publications import retained_validation_assessment
    retained = retained_validation_assessment(inputs, context)
    if retained is not None:
        return retained
    if baseline is None:
        result = UpdateAssessment("first_seen", "exact_material_bytes" if isinstance(evidence, materials) else "no_baseline",
            candidate=evidence.identity.sha256 if isinstance(evidence, materials) else fingerprint(evidence))
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
    elif isinstance(evidence, materials) and isinstance(baseline, materials) and coordinates(evidence) != coordinates(baseline):
        result = UpdateAssessment("changed", "explicit_publication_coordinates",
            ("cbr.same_bytes_do_not_erase_distinct_publication_coordinates",),
            fingerprint(coordinates(baseline)), fingerprint(coordinates(evidence)))
    elif isinstance(evidence, materials) and isinstance(baseline, materials):
        result = UpdateAssessment("unchanged" if evidence.identity == baseline.identity else "changed",
            "exact_material_bytes", predecessor=baseline.identity.sha256, candidate=evidence.identity.sha256)
    else:
        result = UpdateAssessment("unknown", "insufficient_comparable_evidence")
    return {"assessment": result}


def _inline_format(value):
    """Physical fallback for already buffered input; no provider access."""
    data = value.data
    if data.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        return "rar"
    if data.startswith(b"PK"):
        from io import BytesIO
        from zipfile import BadZipFile, ZipFile
        try:
            with ZipFile(BytesIO(data)) as archive:
                if len(archive.infolist()) > 20000:
                    raise ValueError("cbr.material_archive_member_limit")
                names = set(archive.namelist())
                if {"[Content_Types].xml", "xl/workbook.xml"} <= names:
                    content_types = archive.getinfo("[Content_Types].xml")
                    if content_types.file_size > 1_000_000:
                        raise ValueError("cbr.material_content_types_limit")
                    if ("xl/vbaProject.bin" in names
                            or b"macroenabled" in archive.read(content_types).lower()):
                        return "xlsm"
                    return "xlsx"
                if {"[Content_Types].xml", "xl/workbook.bin"} <= names:
                    return "xlsb"
                return "zip"
        except BadZipFile as error:
            raise ValueError("cbr.material_archive_envelope_invalid") from error
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    if data.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
        return "html"
    if len(data) >= 32 and data[0] in {0x02, 0x03, 0x04, 0x05, 0x30, 0x31, 0x32, 0x43, 0x63, 0x83, 0x8B, 0xCB, 0xF5}:
        return "dbf"
    raise ValueError("cbr.material_format_signature_required")


def _inspected_format(value, inspection, context):
    from stratbox.shared.data.materials import MaterialInspection
    if inspection is not None:
        if not isinstance(inspection, MaterialInspection) or inspection.material_identity != value.identity:
            raise ValueError("cbr.material_inspection_mismatch")
        verify = getattr(context, "verify_material_inspection", None)
        if verify is not None and verify(inspection, value):
            return inspection.format
    if isinstance(value, Material):
        detected = _inline_format(value)
        if inspection is not None and inspection.format != detected:
            raise ValueError("cbr.material_inspection_mismatch")
        return detected
    raise ValueError("cbr.accepted_material_inspection_required")


def _form_coordinates(locator):
    match = re.fullmatch(r"(?P<form>\d{3})-(?P<date>\d{8})\.(?:rar|zip|dbf)",
        PurePosixPath(urlsplit(locator).path).name, re.I)
    if match is None or _date(match["date"]) is None:
        raise ValueError("cbr.form_locator_unqualified")
    return "form-0409" + match["form"], _date(match["date"])


def _observed_locator(fetch, request):
    """Resolve privacy-safe transport evidence without inventing a path."""
    from hashlib import sha256
    if not isinstance(request, RequestSpec):
        return None
    identity = sha256(request.url.encode()).hexdigest()
    if fetch.route_id is not None:
        return request.url if fetch.logical_target_identity == identity else None
    locator = fetch.effective_locator
    if locator is None:
        return request.url if fetch.actual_target_identity == identity else None
    parts = urlsplit(locator)
    if parts.path in {"", "/"}:
        if (parts.scheme != "https" or parts.hostname not in CBR_ACCESS.hosts
                or parts.username or parts.password or parts.fragment or parts.query or parts.port not in {None, 443}):
            raise ValueError("cbr.material_request_mismatch")
        return request.url if fetch.actual_target_identity == identity else None
    return _allowed(locator)


def identify(inputs, settings, context):
    from stratbox.shared.data.values import ImmutableMaterialRef
    from stratbox.shared.data.materials import StagedMaterialRef
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
    supplied = inputs["material"]
    value = supplied.material if isinstance(supplied, IdentifiedMaterial) else supplied
    if not isinstance(value, (Material, ImmutableMaterialRef, StagedMaterialRef)):
        raise ValueError("cbr.material_claim_required")
    asset, request, fetch = inputs.get("asset"), inputs.get("request"), inputs.get("evidence")
    if asset is not None and (not isinstance(asset, PublicationAsset) or not _asset_matches(asset, settings)
            or asset.format not in settings.formats):
        raise ValueError("cbr.material_asset_mismatch")
    origin = asset.source_id if asset is not None else value.source_id or settings.series_id
    relation = origin != settings.series_id
    if origin not in {settings.series_id, getattr(settings, "feed_id", None)}:
        raise ValueError("cbr.material_source_mismatch")
    declared_claim = inputs.get("claim") or (supplied.claim if isinstance(supplied, IdentifiedMaterial) else None)
    issue = asset.issue_id if asset is not None else str(_parameters(context).get("issue_id",
        value.metadata.get("issue_id") or (declared_claim.issue_id if isinstance(declared_claim, SourceClaim) else "")))
    asset_id = asset.asset_id if asset is not None else str(value.metadata.get("asset_id")
        or (declared_claim.asset_id if isinstance(declared_claim, SourceClaim) else "main"))
    if relation and asset_id != settings.feed_asset_id:
        raise ValueError("cbr.material_asset_mismatch")
    if request is not None:
        if not isinstance(request, RequestSpec) or request.source_id != origin:
            raise ValueError("cbr.material_request_mismatch")
        _allowed(request.url)
        if asset is not None and request.url != asset.locator:
            raise ValueError("cbr.material_asset_mismatch")
        if (settings.locator and settings.publication_kind in {"fixed", "page"}
                and request.url != settings.locator):
            raise ValueError("cbr.material_request_mismatch")
        path = urlsplit(request.url).path
        if settings.filename_pattern:
            match = re.search(settings.filename_pattern, path, re.I)
            if match is None:
                raise ValueError("cbr.material_request_mismatch")
            token = match.groupdict().get("date")
            located_issue = _date(token)
            if located_issue is None and token and len(token) == 8:
                located_issue = _date(token[4:] + token[2:4] + token[:2])
            if token and located_issue != issue:
                raise ValueError("cbr.material_issue_mismatch")
        if settings.publication_kind == "escrow_index":
            fmt = PurePosixPath(path).suffix.lstrip(".").lower()
            if _escrow_issue(path, fmt) != issue:
                raise ValueError("cbr.material_issue_mismatch")
    verified = (isinstance(request, RequestSpec) and isinstance(fetch, FetchEvidence)
        and fetch.request_identity == request_identity(request) and fetch.material_identity == value.identity
        and (200 <= fetch.status_code < 300 or fetch.status_code == 304
            and getattr(fetch, "validation_kind", "body") == "retained_validation"
            and bool(getattr(fetch, "retained_effect_id", None))
            and bool(getattr(fetch, "representation_identity", None))))
    if verified:
        accepted = getattr(context, "accepted_input", None)
        record = accepted("evidence") if accepted is not None else None
        producer = record.get("produced_by") if isinstance(record, Mapping) else getattr(record, "produced_by", None)
        verified = producer in {"command.material.fetch", "command.material.receive"}
    observed_locator = _observed_locator(fetch, request) if isinstance(fetch, FetchEvidence) else None
    if verified and observed_locator != request.url:
        verified = False
    transport_verified = verified
    if (verified and settings.publication_kind == "escrow_index"
            and "/collection/collection/file/" in urlsplit(request.url).path.lower()):
        # An opaque collection number plus a date cannot prove table membership.
        verified = False
    if not verified:
        verify_use = getattr(context, "verify_source_use", None)
        verified = verify_use is not None and any(use.coordinate.source_id == origin
            and use.coordinate.issue_id == (issue or None) and use.coordinate.asset_id == asset_id
            and use.coordinate.material_identity == value.identity and verify_use(use)
            for use in getattr(supplied, "source_uses", ()))
    claim = declared_claim or SourceClaim(origin, issue, asset_id,
        "verified" if verified else "recognized" if transport_verified else "asserted")
    if not isinstance(claim, SourceClaim) or claim.source_id != origin or value.source_id not in {None, origin}:
        raise ValueError("cbr.material_source_mismatch")
    if claim.issue_id or settings.issue_required:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", claim.issue_id) or _date(claim.issue_id) != claim.issue_id:
            raise ValueError("cbr.issue_date_invalid")
    if claim.issue_id != issue or claim.asset_id != asset_id:
        raise ValueError("cbr.material_asset_mismatch")
    if value.metadata.get("issue_id") not in {None, "", issue} or value.metadata.get("asset_id") not in {None, "", asset_id}:
        raise ValueError("cbr.material_asset_mismatch")
    if claim.attribution == "verified" and not verified:
        raise ValueError("cbr.verified_attribution_requires_evidence")
    if origin == "cbr.reporting_forms.publications":
        locator = asset.locator if asset is not None else request.url if request is not None else None
        if locator is None or _form_coordinates(locator) != (asset_id, issue):
            raise ValueError("cbr.form_locator_unqualified")
        if observed_locator is not None and _form_coordinates(observed_locator) != (asset_id, issue):
            raise ValueError("cbr.form_locator_unqualified")
    if relation and not verified:
        raise ValueError("cbr.feed_relation_verified_origin_required")
    detected = _inspected_format(value, inputs.get("inspection"), context)
    if detected not in settings.formats:
        raise ValueError("cbr.material_format_unavailable")
    if asset is not None and detected != asset.format:
        raise ValueError("cbr.material_asset_format_mismatch")
    media = value.media_type.partition(";")[0].strip().lower()
    declared = {"application/rar": "rar", "application/x-rar": "rar", "application/x-rar-compressed": "rar",
        "application/zip": "zip", "application/x-zip-compressed": "zip", "text/html": "html",
        "application/xhtml+xml": "html", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-excel": "xls"}.get(media)
    if declared is not None and detected != declared and not (declared == "zip" and detected in {"xlsx", "xlsb"}):
        raise ValueError("cbr.material_media_signature_mismatch")
    uses = tuple(getattr(supplied, "source_uses", ())) or tuple(getattr(value, "source_uses", ()))
    if verified:
        uses += (SourceUse(SourceCoordinate(source_id=origin, issue_id=issue or None,
            asset_id=asset_id, material_identity=value.identity), "publication_acquisition", "verified",
            "sha256:" + value.identity.sha256),)
    elif transport_verified:
        uses += (SourceUse(SourceCoordinate(source_id=origin, issue_id=issue or None,
            asset_id=asset_id, material_identity=value.identity), "publication_acquisition",
            "explicit_selected_asset", "sha256:" + value.identity.sha256),)
    if relation:
        uses += (SourceUse(SourceCoordinate(source_id=settings.series_id, family_id=settings.feed_id,
            issue_id=issue, asset_id=asset_id, material_identity=value.identity), "publication_membership",
            "domain_validated", "sha256:" + value.identity.sha256),)
    uses = tuple(dict.fromkeys(uses))
    assessment = Assessment("complete", qualifications=frozenset({"physical_envelope_verified",
        "verified_source" if verified else "explicit_selected_asset" if transport_verified else "caller_asserted_source"}))
    return {"material": IdentifiedMaterial(value, claim, assessment, source_uses=uses), "assessment": assessment}
