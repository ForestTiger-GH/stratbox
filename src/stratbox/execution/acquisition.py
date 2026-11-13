"""Convert admitted HTTP representations into exact source-byte evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from email.message import Message
from typing import BinaryIO, Callable

from stratbox.base.net import HttpFailure, HttpRequest, HttpTransport, RetryPolicy, exchange, exchange_into
from stratbox.data import AcquiredSource, AcquisitionReceipt, ByteIdentity, SourcePayload, canonical_manifest_bytes

from .contracts import OperationFailure
from .runner import Invocation


@dataclass(frozen=True, slots=True)
class StreamBaseline:
    receipt: AcquisitionReceipt
    charset: str | None
    copy_to: Callable[[BinaryIO], None]


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
    receipt, charset, data = _receive(
        request, transport=transport, source_id=source_id, invocation=invocation,
        media_types=media_types, default_media_type=default_media_type, retry=retry,
        baseline=baseline,
    )
    return AcquiredSource(SourcePayload(data, receipt.media_type, source_id, charset=charset), receipt)


def receive_stream(
    request, sink, *, transport, source_id, invocation, media_types,
    default_media_type=None, retry=None, baseline=None,
):
    """Stage admitted source bytes and report the same acquisition evidence as the buffer path."""
    receipt, charset, _ = _receive(
        request, transport=transport, source_id=source_id, invocation=invocation,
        media_types=media_types, default_media_type=default_media_type, retry=retry,
        baseline=baseline, sink=sink,
    )
    return receipt, charset


def _receive(
    request, *, transport, source_id, invocation, media_types,
    default_media_type, retry, baseline, sink=None,
):
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
        and baseline.receipt.identity.size <= request.max_response_bytes
        and baseline.receipt.media_type in media_types
        and (not managed or (
            baseline.receipt.origin_assurance == "peer_bound" and baseline.receipt.target_sha256
        ))
        else None
    )
    if prior is not None and managed:
        verifier = getattr(transport, "verify_baseline", None)
        if isinstance(baseline, StreamBaseline) or not callable(verifier) or verifier(baseline) is not True:
            prior = None
    if prior is not None:
        request = replace(request, headers={**request.headers, "if-none-match": prior.etag})
    options = dict(transport=transport, retry=retry, budget=invocation.budget, cancelled=invocation.cancelled)
    result = exchange(request, **options) if sink is None else exchange_into(request, sink, **options)
    if isinstance(result, HttpFailure):
        if result.reason == "cancelled":
            raise OperationFailure("operation.cancelled", outcome="cancelled")
        if result.reason == "capability_missing":
            raise OperationFailure("provider.capability_missing")
        if result.reason == "staging_failed":
            raise OperationFailure("effect.staging_failed")
        raise OperationFailure(f"http.{result.reason}", component=f"http.{result.stage}")
    response = result if sink is None else result.response
    if managed and response.origin_assurance != "peer_bound":
        raise OperationFailure("http.destination_unqualified")
    if response.status_code == 304:
        if (
            prior is None
            or prior.safe_locator != response.effective_locator_safe
            or prior.target_sha256 != response.target_sha256
            or response.headers.get("etag", prior.etag) != prior.etag
            or (response.body if sink is None else result.identity.size)
        ):
            raise OperationFailure("http.full_representation_required")
        reused = replace(prior, status_code=304, observed_at_utc=response.observed_at_utc,
                         reused=True, wire_size=response.wire_size)
        if isinstance(baseline, StreamBaseline):
            try:
                baseline.copy_to(sink)
            except OperationFailure as error:
                if error.outcome == "cancelled":
                    raise
                raise OperationFailure("http.full_representation_required") from None
            return reused, baseline.charset, b""
        if sink is not None:
            invocation.budget.charge("input_bytes", baseline.payload.identity.size)
            for start in range(0, baseline.payload.identity.size, 65536):
                invocation.check_cancelled()
                chunk = baseline.payload.data[start:start + 65536]
                if sink.write(chunk) != len(chunk):
                    raise OperationFailure("effect.staging_failed")
        return reused, baseline.payload.charset, baseline.payload.data
    if response.status_code != 200:
        raise OperationFailure(f"http.status_{response.status_code}")
    mime = (
        response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        or default_media_type
    )
    if mime is None or mime not in media_types:
        raise OperationFailure("source.media_type_unexpected")
    identity = ByteIdentity.of(response.body) if sink is None else result.identity
    if not identity.size:
        raise OperationFailure("source.empty")
    metadata = Message()
    if "content-type" in response.headers:
        metadata["content-type"] = response.headers["content-type"]
    receipt = AcquisitionReceipt(
        source_id, identity, response.observed_at_utc, mime, response.status_code,
        response.effective_locator_safe, response.origin_assurance, fingerprint,
        response.target_sha256, response.headers.get("etag"),
        content_encoding=response.headers.get("content-encoding", "identity").strip().lower() or "identity",
        wire_size=response.wire_size,
    )
    return receipt, metadata.get_content_charset(), response.body
