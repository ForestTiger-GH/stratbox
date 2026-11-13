"""Convert admitted HTTP representations into exact source-byte evidence."""

from __future__ import annotations

from dataclasses import replace
from email.message import Message

from stratbox.base.net import HttpFailure, HttpRequest, HttpTransport, RetryPolicy, exchange
from stratbox.data import AcquiredSource, AcquisitionReceipt, ByteIdentity, SourcePayload, canonical_manifest_bytes

from .contracts import OperationFailure
from .runner import Invocation


def _request_identity(request: HttpRequest, invocation: Invocation, transport: HttpTransport) -> str:
    binding = next(
        (item for item in invocation.context.bindings
         if item.capability.role == "http" and item.provider is transport), None
    )
    return ByteIdentity.of(canonical_manifest_bytes({
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "form": dict(request.form_fields) if request.form_fields is not None else None,
        "body": ByteIdentity.of(request.body).sha256 if request.body is not None else None,
        "provider": binding.provider_id if binding else f"{type(transport).__module__}.{type(transport).__qualname__}",
        "profile": invocation.context.profile,
        "scope": binding.scope_id if binding else None,
    })).sha256


def receive_source(
    request: HttpRequest,
    *,
    transport: HttpTransport,
    source_id: str,
    invocation: Invocation,
    media_types: frozenset[str],
    default_media_type: str | None = None,
    retry: RetryPolicy | None = None,
    baseline: AcquiredSource | None = None,
) -> AcquiredSource:
    invocation.require_provider("http", transport)
    fingerprint = _request_identity(request, invocation, transport)
    managed = invocation.context.profile == "managed"
    if managed and not getattr(transport, "accounts_http_budget", False):
        raise OperationFailure("provider.guarantee_missing")
    prior = (
        baseline.receipt if baseline is not None and request.method == "GET"
        and baseline.receipt.source_id == source_id
        and baseline.receipt.request_sha256 == fingerprint
        and request.headers.keys() <= {"accept", "accept-encoding", "user-agent"}
        and baseline.receipt.target_sha256
        and baseline.receipt.etag and not baseline.receipt.etag.startswith("W/")
        and baseline.receipt.etag.startswith('"') and baseline.receipt.etag.endswith('"')
        and baseline.payload.identity.size <= request.max_response_bytes
        and baseline.receipt.media_type in media_types
        and (not managed or (
            baseline.receipt.origin_assurance == "peer_bound" and baseline.receipt.target_sha256
        ))
        else None
    )
    if prior is not None and managed:
        verifier = getattr(transport, "verify_baseline", None)
        if not callable(verifier) or verifier(baseline) is not True:
            prior = None
    if prior is not None:
        request = replace(request, headers={**request.headers, "if-none-match": prior.etag})
    cancellation = invocation.context.cancellation
    result = exchange(
        request, transport=transport, retry=retry, budget=invocation.budget,
        cancelled=cancellation.is_set if cancellation is not None else None,
    )
    if isinstance(result, HttpFailure):
        if result.reason == "cancelled":
            raise OperationFailure("operation.cancelled", outcome="cancelled")
        if result.reason == "capability_missing":
            raise OperationFailure("provider.capability_missing")
        raise OperationFailure(f"http.{result.reason}", component=f"http.{result.stage}")
    if managed and result.origin_assurance != "peer_bound":
        raise OperationFailure("http.destination_unqualified")
    if result.status_code == 304:
        if (
            prior is None
            or prior.safe_locator != result.effective_locator_safe
            or prior.target_sha256 != result.target_sha256
            or result.headers.get("etag", prior.etag) != prior.etag
        ):
            raise OperationFailure("http.full_representation_required")
        return AcquiredSource(baseline.payload, replace(
            prior, status_code=304, observed_at_utc=result.observed_at_utc, reused=True,
        ))
    if result.status_code != 200:
        raise OperationFailure(f"http.status_{result.status_code}")
    mime = (
        result.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        or default_media_type
    )
    if mime is None or mime not in media_types:
        raise OperationFailure("source.media_type_unexpected")
    if not result.body:
        raise OperationFailure("source.empty")
    metadata = Message()
    if "content-type" in result.headers:
        metadata["content-type"] = result.headers["content-type"]
    payload = SourcePayload(
        result.body, mime, source_id, charset=metadata.get_content_charset()
    )
    receipt = AcquisitionReceipt(
        source_id, payload.identity, result.observed_at_utc, mime, result.status_code,
        result.effective_locator_safe, result.origin_assurance, fingerprint,
        result.target_sha256, result.headers.get("etag"),
    )
    return AcquiredSource(payload, receipt)
