"""Report bounded source validation facts without copying source values into events."""

import re

from stratbox.data import SourcePayload, UsedInputReceipt

from .contracts import OperationFailure
from .runner import Invocation


def use_payload(
    payload: SourcePayload, invocation: Invocation, *, role: str, limit: int
) -> None:
    if not isinstance(payload, SourcePayload):
        raise OperationFailure("input.payload_required")
    if not 0 < payload.identity.size <= limit:
        raise OperationFailure("source.size_limit")
    invocation.use(UsedInputReceipt.for_payload(payload, role))


def decode_html(payload: SourcePayload) -> str:
    try:
        text = payload.data.decode(payload.charset or "utf-8", errors="strict")
    except (UnicodeError, LookupError, TypeError):
        raise OperationFailure("source.charset_invalid") from None
    if "\x00" in text or "\ufffd" in text:
        raise OperationFailure("source.charset_invalid")
    return text


def source_failure(error: Exception) -> OperationFailure:
    # Source validators carry fixed uppercase reason codes. Their optional
    # text after a colon can contain source data and stays out of diagnostics.
    reason = str(error).split(":", 1)[0]
    if re.fullmatch(r"[A-Z][A-Z0-9_]{0,90}", reason):
        return OperationFailure(f"source.{reason.lower()}")
    if re.fullmatch(r"archive\.[a-z_]{1,64}", reason):
        if reason in {
            "archive.rar_provider_missing",
            "archive.rar_extractor_unavailable",
        }:
            return OperationFailure("provider.capability_missing")
        return OperationFailure(reason)
    return OperationFailure("source.content_invalid")
