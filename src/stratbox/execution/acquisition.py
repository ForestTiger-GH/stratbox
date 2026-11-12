"""Convert a successful HTTP representation into exact source-byte evidence."""

from __future__ import annotations

from email.message import Message

from stratbox.base.net import (
    HttpFailure,
    HttpRequest,
    HttpTransport,
    RetryPolicy,
    exchange,
)
from stratbox.data import AcquiredSource, AcquisitionReceipt, SourcePayload

from .contracts import OperationFailure
from .runner import Invocation


def receive_source(
    request: HttpRequest,
    *,
    transport: HttpTransport,
    source_id: str,
    invocation: Invocation,
    media_types: frozenset[str],
    default_media_type: str | None = None,
    retry: RetryPolicy | None = None,
) -> AcquiredSource:
    cancellation = invocation.context.cancellation
    result = exchange(
        request,
        transport=transport,
        retry=retry,
        cancelled=cancellation.is_set if cancellation is not None else None,
    )
    if isinstance(result, HttpFailure):
        if result.reason == "cancelled":
            raise OperationFailure("operation.cancelled", outcome="cancelled")
        if result.reason == "capability_missing":
            raise OperationFailure("provider.capability_missing")
        raise OperationFailure(f"http.{result.reason}")
    if result.status_code != 200:
        code = (
            "http.full_representation_required"
            if result.status_code == 304
            else f"http.status_{result.status_code}"
        )
        raise OperationFailure(code)
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
        source_id,
        payload.identity,
        result.observed_at_utc,
        mime,
        result.status_code,
        result.effective_locator_safe,
    )
    return AcquiredSource(payload, receipt)
