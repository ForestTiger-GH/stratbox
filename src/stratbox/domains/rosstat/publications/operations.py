"""Independent discovery and verified publisher-original acquisition."""

from __future__ import annotations

from stratbox.core.execution import (
    Completion, ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.network import HttpTransport, RetryPolicy, StreamingHttpTransport
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.originals import (
    ReceiveOriginalRequest, ReceiveToStoreRequest, receive_original_to_store,
)
from stratbox.core.operations.source.validation import decode_html, use_payload
from stratbox.domains.rosstat._source import (
    MEDIA_TYPES, allowed_file_url, file_request, page_request,
)
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

from .catalog import get_rosstat_source
from .contracts import (
    AcquireRosstatRequest, AcquireRosstatToStoreRequest, AcquiredRosstatAsset,
    DiscoverRosstatRequest, RosstatPublicationIndex, StoredRosstatAsset,
)
from .discovery.profiles import profile_for, qualify_index
from .discovery.families.rules import parse_issue
from .download.envelope import detect_bytes, detect_envelope

from .definitions import (
    ACQUIRE, ACQUIRE_TO_STORE, DISCOVER, _HTTP, _LIMIT, _OUTPUT, _WRITE,
)

_HTML = frozenset({"text/html", "application/xhtml+xml"})
_FORMAT_LIMITS = {"pdf": 100 * 1024 * 1024, "xlsx": 100 * 1024 * 1024,
                  "zip": _LIMIT, "rar": _LIMIT}


def discover(
    request: DiscoverRosstatRequest, *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[RosstatPublicationIndex]:
    def work(req, invocation):
        try:
            spec = get_rosstat_source(req.series_id)
        except ValueError:
            raise OperationFailure("rosstat.series_unknown") from None
        payload = req.index
        acquisition = None
        if payload is None:
            invocation.stage("acquire_publication_page")
            source = receive_source(
                page_request(spec.landing_url, spec.landing_url),
                transport=invocation.provider("http", transport),
                source_id=req.series_id + ".index",
                invocation=invocation,
                media_types=_HTML,
                retry=RetryPolicy(),
            )
            payload = source.payload
            acquisition = source.receipt
        if not isinstance(payload, SourcePayload):
            raise OperationFailure("input.payload_required")
        if payload.source_id != req.series_id + ".index":
            raise OperationFailure("rosstat.index_source_mismatch")
        if payload.media_type not in _HTML:
            raise OperationFailure("rosstat.index_media_type_unexpected")
        use_payload(payload, invocation, role="publisher_index", limit=10 * 1024 * 1024)
        invocation.stage("qualify_publication_links")
        try:
            return qualify_index(req.series_id, payload, text=decode_html(payload), acquisition=acquisition)
        except ValueError as error:
            code = str(error)
            if code in {
                "rosstat.html_limit", "rosstat.html_link_limit",
                "rosstat.html_label_limit", "rosstat.html_base_forbidden",
                "rosstat.index_unrecognized",
            }:
                raise OperationFailure(code) from None
            raise OperationFailure("rosstat.index_unrecognized") from None
    return run(DISCOVER, request, work, context=context, providers={"http": transport})


def _admit(asset, *, size_limit, deadline):
    if asset.key is None or asset.qualification != "qualified":
        raise OperationFailure("rosstat.asset_unqualified")
    try:
        spec = get_rosstat_source(asset.key.issue.series_id)
    except ValueError:
        raise OperationFailure("rosstat.series_unknown") from None
    if asset.profile_version != profile_for(asset.key.issue.series_id).profile_version or asset.landing_url != spec.landing_url:
        raise OperationFailure("rosstat.asset_profile_mismatch")
    if (asset.declared_format not in spec.accepted_formats or not allowed_file_url(asset.url)
            or asset.index_identity.size == 0 or not asset.issue_evidence):
        raise OperationFailure("rosstat.asset_url_forbidden")
    # Re-run profile interpretation against the candidate's own provenance.
    # This is consistency validation, not a cryptographic publisher proof.
    rule = profile_for(spec.series_id)
    issue_id, _, diagnostics = parse_issue(rule, asset.filename, asset.label_literal)
    asset_id, asset_role, _ = rule.asset_id(asset.label_literal, asset.filename)
    from urllib.parse import unquote, urlsplit
    from pathlib import PurePosixPath
    if (
        diagnostics or issue_id != asset.key.issue.issue_id
        or asset_id != asset.key.asset_id or asset_role != asset.asset_role
        or PurePosixPath(unquote(urlsplit(asset.url).path)).name != asset.filename
        or not asset.url.lower().endswith("." + asset.declared_format)
    ):
        raise OperationFailure("rosstat.asset_identity_unverified")
    if type(size_limit) is not int or not 0 < size_limit <= _FORMAT_LIMITS[asset.declared_format]:
        raise OperationFailure("rosstat.acquisition_limit_invalid")
    if not 1 <= deadline <= 600:
        raise OperationFailure("rosstat.acquisition_deadline_invalid")
    try:
        return file_request(asset.url, size_limit, deadline)
    except ValueError:
        raise OperationFailure("rosstat.asset_url_forbidden") from None


def acquire(
    request: AcquireRosstatRequest, *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredRosstatAsset]:
    def work(req, invocation):
        http = _admit(req.asset, size_limit=req.max_bytes, deadline=req.deadline_seconds)
        invocation.stage("receive_original")
        original = receive_source(
            http, transport=invocation.provider("http", transport),
            source_id=req.asset.key.source_id, invocation=invocation,
            media_types=MEDIA_TYPES, default_media_type="application/octet-stream",
            retry=req.retry,
        )
        invocation.use(UsedInputReceipt.for_payload(original.payload, "publisher_original"))
        invocation.stage("verify_original_envelope")
        detected = detect_bytes(original.payload.data, expected=req.asset.declared_format)
        return AcquiredRosstatAsset(req.asset, original, detected)
    return run(ACQUIRE, request, work, context=context, providers={"http": transport})


def acquire_to_store(
    request: AcquireRosstatToStoreRequest, *,
    transport: StreamingHttpTransport | None = None,
    store=None,
    baseline_store=None,
    context: ExecutionContext | None = None,
) -> OperationResult[StoredRosstatAsset]:
    def work(req, invocation):
        http = _admit(req.asset, size_limit=req.max_bytes, deadline=req.deadline_seconds)
        invocation.stage("receive_and_verify_original")
        detected = None

        def validate(stream, size):
            nonlocal detected
            detected = detect_envelope(stream, expected=req.asset.declared_format, size=size)

        source = ReceiveOriginalRequest(
            http, req.asset.key.source_id, MEDIA_TYPES,
            retry=req.retry, default_media_type="application/octet-stream",
        )
        stored = receive_original_to_store(
            ReceiveToStoreRequest(source, req.destination, req.baseline),
            transport=invocation.provider("http", transport),
            store=invocation.provider("output_filestore", store),
            invocation=invocation, validate=validate,
            baseline_store=baseline_store,
        )
        if detected is None:
            raise OperationFailure("rosstat.original_envelope_unverified")
        result = StoredRosstatAsset(req.asset, stored, detected)
        if stored.storage.status in {"unknown", "failed"}:
            return Completion(result, stored.storage.status, stored.storage.diagnostic_code)
        return result

    return run(
        ACQUIRE_TO_STORE, request, work, context=context,
        providers={"http": transport, "output_filestore": store, "filestore": baseline_store},
    )
