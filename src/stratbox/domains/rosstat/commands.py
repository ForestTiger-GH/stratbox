"""Rosstat technical leaves executed by the common capability runner.

Functions accept owned values and use the active invocation directly. No leaf
creates a second execution session or calls an operation handler.
"""
from __future__ import annotations

from dataclasses import replace


def _guard(function):
    """Keep deliberate domain validation codes at the command boundary."""
    from functools import wraps
    import re
    @wraps(function)
    def guarded(request, invocation):
        from stratbox.core.execution.contracts import OperationFailure
        try:
            return function(request, invocation)
        except ValueError as error:
            code = str(error)
            if not re.fullmatch(r"[a-z][a-z0-9_.]+", code):
                code = "rosstat.input_invalid"
            raise OperationFailure(code) from None
    return guarded


def _use(request, invocation):
    from .operations.evidence import use_value
    for name, value in request.items():
        if value is not None:
            use_value(value, invocation, name)
            edition = getattr(value, "territory_edition", None)
            if edition is not None:
                use_value(edition, invocation, "territory_edition")
    invocation.check_cancelled()


def _finish(value, invocation, *, partial=False):
    invocation.check_cancelled()
    from .operations.evidence import _snapshot
    from stratbox.core.execution.values import account_value
    identity = account_value(value, invocation, snapshot_factory=_snapshot)
    invocation.record(identity)
    coverage = getattr(value, "coverage", None)
    if partial and coverage is not None and getattr(coverage, "status", None) != "complete":
        from stratbox.core.execution.runner import Completion
        return Completion(value, "partial", "rosstat.source_scope_qualified")
    return value


@_guard
def qualify_index(request, invocation):
    from .publications.catalog import get_rosstat_source
    from .publications.discovery.profiles import qualify_index as qualify
    from stratbox.core.operations.source.validation import decode_html, use_payload
    from stratbox.shared.evidence import SourcePayload
    source = get_rosstat_source(request["series_id"])
    payload = request["index"]
    if not isinstance(payload, SourcePayload) or payload.source_id != source.series_id + ".index":
        raise ValueError("rosstat.index_source_mismatch")
    if payload.media_type not in {"text/html", "application/xhtml+xml"}:
        raise ValueError("rosstat.index_media_type_unexpected")
    use_payload(payload, invocation, role="publisher_index", limit=10 * 1024 * 1024)
    return qualify(source.series_id, payload, text=decode_html(payload))


@_guard
def receive_index(request, invocation):
    from .publications.catalog import get_rosstat_source
    from .publications.access import page_request
    from stratbox.core.operations.source.acquisition import receive_source
    from stratbox.core.network import RetryPolicy
    source = get_rosstat_source(request["series_id"])
    acquired = receive_source(page_request(source.landing_url, source.landing_url),
        transport=invocation.provider("http"), source_id=source.series_id + ".index",
        invocation=invocation, media_types=frozenset({"text/html", "application/xhtml+xml"}), retry=RetryPolicy())
    return acquired.payload


@_guard
def select_assets(request, invocation):
    from .publications.discovery.selection import select_assets as select
    _use(request, invocation)
    return select(request["index"], **{name: request[name] for name in ("issue_ids", "asset_roles", "policy", "max_assets")})


@_guard
def plan_updates(request, invocation):
    from .publications.discovery.selection import compare_publication_indices
    _use(request, invocation)
    return compare_publication_indices(request["before"], request["after"])


@_guard
def review_index(request, invocation):
    from .publications.discovery.approval import approve_index
    _use(request, invocation)
    return approve_index(request["index"], request["evidence"])


@_guard
def admit_asset(request, invocation):
    """Validate publisher identity and bounded transfer before network work."""
    from .publications.catalog import get_rosstat_source
    from .publications.discovery.profiles import profile_for
    from .publications.discovery.families.rules import parse_issue
    from .publications.access import allowed_file_url, file_request
    from pathlib import PurePosixPath
    from urllib.parse import unquote, urlsplit
    asset = request["asset"]
    if asset.key is None or asset.qualification != "qualified":
        raise ValueError("rosstat.asset_unqualified")
    source = get_rosstat_source(asset.series_id)
    rule = profile_for(asset.series_id)
    if asset.profile_version != rule.profile_version or asset.landing_url != source.landing_url:
        raise ValueError("rosstat.asset_profile_mismatch")
    if (asset.declared_format not in source.accepted_formats or not allowed_file_url(asset.url)
            or not asset.index_identity.size or not asset.issue_evidence):
        raise ValueError("rosstat.asset_url_forbidden")
    issue_id, _, diagnostics = parse_issue(rule, asset.filename, asset.label_literal)
    asset_id, role, _ = rule.asset_id(asset.label_literal, asset.filename)
    if (diagnostics or issue_id != asset.key.issue.issue_id or asset_id != asset.key.asset_id
            or role != asset.asset_role or PurePosixPath(unquote(urlsplit(asset.url).path)).name != asset.filename
            or not asset.url.lower().endswith("." + asset.declared_format)):
        raise ValueError("rosstat.asset_identity_unverified")
    limits = {"pdf": 100 * 1024**2, "xlsx": 100 * 1024**2, "zip": 256 * 1024**2, "rar": 256 * 1024**2}
    size, deadline = request["max_bytes"], request["deadline_seconds"]
    if type(size) is not int or not 0 < size <= limits[asset.declared_format]:
        raise ValueError("rosstat.acquisition_limit_invalid")
    if not 1 <= deadline <= 600:
        raise ValueError("rosstat.acquisition_deadline_invalid")
    return file_request(asset.url, size, deadline)


@_guard
def receive_asset(request, invocation):
    from stratbox.core.operations.source.acquisition import receive_source
    from .publications.access import MEDIA_TYPES
    acquired = receive_source(request["request"], transport=invocation.provider("http"),
        source_id=request["asset"].key.source_id, invocation=invocation, media_types=MEDIA_TYPES,
        default_media_type="application/octet-stream", retry=request["retry"])
    return acquired


@_guard
def verify_envelope(request, invocation):
    from .publications.download.envelope import detect_bytes
    from .publications.contracts import AcquiredRosstatAsset
    from stratbox.shared.evidence import UsedInputReceipt
    source, asset = request["original"], request["asset"]
    if source.payload.source_id != asset.key.source_id:
        raise ValueError("rosstat.original_source_mismatch")
    invocation.use(UsedInputReceipt.for_payload(source.payload, "publisher_original"))
    detected = detect_bytes(source.payload.data, expected=asset.declared_format)
    return {"payload": source.payload, "acquired": AcquiredRosstatAsset(asset, source, detected)}


@_guard
def receive_to_store(request, invocation):
    from stratbox.core.operations.source.originals import receive_original_to_store
    from stratbox.core.operations.source.original_definitions import ReceiveOriginalRequest, ReceiveToStoreRequest
    from .publications.access import MEDIA_TYPES
    from .publications.download.envelope import detect_envelope
    from .publications.contracts import StoredRosstatAsset
    from stratbox.core.execution.runner import Completion
    asset = request["asset"]
    detected = None
    def validate(stream, size):
        nonlocal detected
        detected = detect_envelope(stream, expected=asset.declared_format, size=size)
    source = ReceiveOriginalRequest(request["request"], asset.key.source_id, MEDIA_TYPES,
        retry=request["retry"], default_media_type="application/octet-stream")
    stored = receive_original_to_store(ReceiveToStoreRequest(source, request["destination"], request.get("baseline")),
        transport=invocation.provider("http"), store=invocation.provider("output_filestore"),
        invocation=invocation, validate=validate)
    if detected is None:
        raise ValueError("rosstat.original_envelope_unverified")
    result = StoredRosstatAsset(asset, stored, detected)
    if stored.storage.status in {"unknown", "failed"}:
        return Completion(result, stored.storage.status, stored.storage.diagnostic_code)
    return result


@_guard
def inspect_archive(request, invocation):
    from .publications.archives import inspect_archive as inspect
    _use(request, invocation)
    return inspect(request["payload"], limits=request["limits"], budget=invocation.budget)


@_guard
def extract_members(request, invocation):
    from .publications.archives import acquire_members
    _use(request, invocation)
    result = acquire_members(request["payload"], request["inventory"], request["names"],
        limits=request["limits"], budget=invocation.budget, checkpoint=invocation.check_cancelled)
    for position, member in enumerate(result):
        invocation.account_output(member.payload.identity, key="member." + str(position))
    return result


def _physical(request, invocation, *, document=False):
    from .publications.catalog import get_rosstat_source
    from stratbox.shared.source_publications import SourceAssetIdentity
    from stratbox.shared.evidence import UsedInputReceipt
    get_rosstat_source(request["series_id"])
    identity = SourceAssetIdentity(request["series_id"], request["issue_id"], request["asset_id"])
    payload, container, member = request["payload"], request.get("container_identity"), request.get("member")
    if payload.source_id is not None and payload.source_id != identity.source_id:
        raise ValueError("rosstat.physical_source_identity_mismatch")
    if (container is None) != (member is None):
        raise ValueError("rosstat.physical_member_lineage_required")
    if request["series_id"] == "rosstat.socioeconomic_regions" and container is None:
        raise ValueError("rosstat.regional_member_lineage_required")
    if document:
        if request["series_id"] not in {"rosstat.socioeconomic_russia", "rosstat.socioeconomic_regions"}:
            raise ValueError("rosstat.family_workbook_required")
        from stratbox.core.formats.documents import extract_document as extract
    else:
        if request["series_id"] == "rosstat.socioeconomic_russia":
            raise ValueError("rosstat.family_document_required")
        from stratbox.core.formats.spreadsheets.extracts import extract_workbook as extract
    result = extract(payload, series_id=identity.series_id, issue_id=identity.issue_id, asset_id=identity.asset_id,
        budget=invocation.budget, checkpoint=invocation.check_cancelled)
    if member is not None:
        receipt = UsedInputReceipt.for_payload(payload, "archive_member", container=container, member=member)
        archive = UsedInputReceipt("regional_archive", container, "application/octet-stream", "reference_only", payload.source_id)
        result = replace(result, lineage=(archive, receipt))
        invocation.use(archive)
        invocation.use(receipt)
    return _finish(result, invocation, partial=document)


@_guard
def extract_workbook(request, invocation):
    _use(request, invocation)
    return _physical(request, invocation)


@_guard
def extract_document(request, invocation):
    _use(request, invocation)
    return _physical(request, invocation, document=True)


@_guard
def extract_kep2(request, invocation):
    from .tables.contracts import Kep2Request
    from .tables.kep2 import extract_kep2 as extract
    _use(request, invocation)
    return _finish(extract(Kep2Request(**request), budget=invocation.budget,
        checkpoint=invocation.check_cancelled), invocation, partial=True)


@_guard
def map_reviewed_cells(request, invocation):
    from .tables.mapping import map_reviewed_cells as map_cells
    _use(request, invocation)
    return _finish(map_cells(request["physical"], request["profile"]), invocation, partial=True)


@_guard
def structure_document(request, invocation):
    from .tables.documents import structure_document as structure
    _use(request, invocation)
    return _finish(structure(request["document"], request["layout"]), invocation, partial=True)


@_guard
def integrate(request, invocation):
    from .integration.datasets import integrate_flakes
    _use(request, invocation)
    return _finish(integrate_flakes(request["flakes"], dataset_id=request["dataset_id"], release_id=request["release_id"]), invocation)


@_guard
def derive_index_growth(request, invocation):
    from .analytics.indicators import derive_index_growth as derive
    _use(request, invocation)
    return _finish(derive(request["dataset"], release_id=request["release_id"]), invocation)


@_guard
def prepare_view(request, invocation):
    from .products.views import prepare_view as prepare
    _use(request, invocation)
    return _finish(prepare(request["dataset"], view_id=request["view_id"], metric_ids=request["metric_ids"]), invocation)


@_guard
def prepare_kep2_monthly(request, invocation):
    from .products.views import prepare_kep2_monthly as prepare
    _use(request, invocation)
    return _finish(prepare(request["dataset"]), invocation)


def _unary(request, invocation, module, name, field, **kwargs):
    from importlib import import_module
    _use(request, invocation)
    value = getattr(import_module(module), name)(request[field], **kwargs)
    return _finish(value, invocation)


def _binary(request, invocation, module, name):
    from importlib import import_module
    _use(request, invocation)
    return _finish(getattr(import_module(module), name)(request["before"], request["after"]), invocation)


@_guard
def workbook_snapshot(r, i):
    return _unary(r, i, "stratbox.shared.data.workbooks", "workbook_snapshot", "workbook")

@_guard
def read_workbook(r, i):
    return _unary(r, i, "stratbox.shared.data.workbooks", "workbook_from_snapshot", "snapshot")

@_guard
def readable_workbook(r, i):
    return _unary(r, i, "stratbox.shared.data.workbooks", "readable_workbook", "workbook")

@_guard
def compare_workbooks(r, i):
    return _binary(r, i, "stratbox.shared.data.workbooks", "compare_workbooks")

@_guard
def document_snapshot(r, i):
    return _unary(r, i, "stratbox.shared.data.documents", "document_snapshot", "document")

@_guard
def read_document(r, i):
    return _unary(r, i, "stratbox.shared.data.documents", "document_from_snapshot", "snapshot")

@_guard
def readable_document(r, i):
    return _unary(r, i, "stratbox.shared.data.documents", "readable_document", "document")

@_guard
def flake_snapshot(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.tables.snapshots", "flake_snapshot", "flake", checkpoint=i.check_cancelled)

@_guard
def read_flake(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.tables.snapshots", "flake_from_snapshot", "snapshot")

@_guard
def readable_flake(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.tables.representation", "readable_flake", "flake")

@_guard
def validate_flake(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.tables.comparison", "validate_flake", "flake")

@_guard
def compare_flakes(r, i):
    return _binary(r, i, "stratbox.domains.rosstat.tables.comparison", "compare_flakes")

@_guard
def dataset_snapshot(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.integration.datasets", "dataset_snapshot", "dataset")

@_guard
def read_dataset(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.integration.datasets", "dataset_from_snapshot", "snapshot")

@_guard
def compare_datasets(r, i):
    return _binary(r, i, "stratbox.domains.rosstat.analytics.indicators", "compare_datasets")

@_guard
def view_snapshot(r, i):
    return _unary(r, i, "stratbox.shared.data.views", "view_snapshot", "view")

@_guard
def read_view(r, i):
    return _unary(r, i, "stratbox.shared.data.views", "view_from_snapshot", "snapshot")

@_guard
def render_view(r, i):
    return _unary(r, i, "stratbox.shared.data.views", "render_observation_view", "view", format=r["format"])

@_guard
def render_kep2_xlsx(r, i):
    return _unary(r, i, "stratbox.domains.rosstat.products.xlsx", "render_kep2_xlsx", "view")


@_guard
def select_member(request, invocation):
    """Project one explicitly selected member without erasing archive lineage."""
    members = request["members"]
    selected = tuple(member for member in members if member.name == request["name"])
    if len(selected) != 1:
        raise ValueError("rosstat.archive_member_selection_invalid")
    member, = selected
    for receipt in member.lineage:
        invocation.use(receipt)
    return {"payload": member.payload, "container_identity": member.container_identity, "member": member.name}


@_guard
def extract_population(request, invocation):
    from .tables.editions import extract_population as extract
    _use(request, invocation)
    return _finish(extract(request["workbook"], selected_rows=request["selected_rows"], invocation=invocation), invocation, partial=True)


@_guard
def extract_regional_industrial_indices(request, invocation):
    from .tables.editions import extract_regional_industrial_indices as extract
    _use(request, invocation)
    return _finish(extract(request["workbook"], selected_rows=request["selected_rows"], selected_years=request["selected_years"], invocation=invocation), invocation, partial=True)
