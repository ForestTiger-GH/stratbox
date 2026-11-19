"""Independent discovery and verified publisher-original acquisition."""

from __future__ import annotations

from stratbox.core.execution import (
    Completion, ExecutionBudget, ExecutionContext, OperationDefinition,
    OperationFailure, OperationResult, run,
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
from stratbox.shared.evidence import UsedInputReceipt

from .catalog import get_rosstat_source
from .contracts import (
    AcquireRosstatRequest, AcquireRosstatToStoreRequest, AcquiredRosstatAsset,
    DiscoverRosstatRequest, RosstatPublicationIndex, StoredRosstatAsset,
)
from .discovery.profiles import PROFILE_VERSION, qualify_index
from .download.envelope import detect_bytes, detect_envelope

_HTML = frozenset({"text/html", "application/xhtml+xml"})
_HTTP = frozenset({"http"})
_OUTPUT = frozenset({"output_filestore"})
_WRITE = frozenset({"storage.write"})
_LIMIT = 256 * 1024 * 1024
_FORMAT_LIMITS = {"pdf": 100 * 1024 * 1024, "xlsx": 100 * 1024 * 1024,
                  "zip": _LIMIT, "rar": _LIMIT}

DISCOVER = OperationDefinition(
    "rosstat.publications.discover", 1, "rosstat-source-links-1",
    DiscoverRosstatRequest, RosstatPublicationIndex, optional_capabilities=_HTTP,
)
ACQUIRE = OperationDefinition(
    "rosstat.publications.acquire", 1, "rosstat-original-envelope-1",
    AcquireRosstatRequest, AcquiredRosstatAsset, _HTTP,
    limits=ExecutionBudget(input_bytes=_LIMIT, output_bytes=_LIMIT, temporary_bytes=_LIMIT),
)
ACQUIRE_TO_STORE = OperationDefinition(
    "rosstat.publications.acquire_to_store", 1, "rosstat-original-stream-1",
    AcquireRosstatToStoreRequest, StoredRosstatAsset, _HTTP | _OUTPUT, _WRITE,
    optional_capabilities=frozenset({"filestore"}),
    limits=ExecutionBudget(input_bytes=_LIMIT, output_bytes=_LIMIT, temporary_bytes=_LIMIT),
)


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
        use_payload(payload, invocation, role="publisher_index", limit=10 * 1024 * 1024)
        invocation.stage("qualify_publication_links")
        try:
            return qualify_index(req.series_id, payload, text=decode_html(payload))
        except (UnicodeError, ValueError):
            raise OperationFailure("rosstat.index_unrecognized") from None
    return run(DISCOVER, request, work, context=context, providers={"http": transport})


def _admit(asset, *, size_limit, deadline):
    if asset.key is None or asset.qualification != "qualified":
        raise OperationFailure("rosstat.asset_unqualified")
    try:
        spec = get_rosstat_source(asset.key.issue.series_id)
    except ValueError:
        raise OperationFailure("rosstat.series_unknown") from None
    if asset.profile_version != PROFILE_VERSION or asset.landing_url != spec.landing_url:
        raise OperationFailure("rosstat.asset_profile_mismatch")
    if asset.declared_format not in spec.accepted_formats or not allowed_file_url(asset.url):
        raise OperationFailure("rosstat.asset_url_forbidden")
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
