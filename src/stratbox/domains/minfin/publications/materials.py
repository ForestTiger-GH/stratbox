"""Publisher-material admission and optional readable document conversion.

These are source-specific actions invoked from registered operation handlers.
The domain never owns HTTP transports, storage effects, or message delivery.
"""
from __future__ import annotations
from stratbox.core.execution import Completion, OperationFailure
from stratbox.core.network import HttpTransport, RetryPolicy
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.validation import use_payload
from .access import FILE_MIMES, file_request
from .catalog import family
from .contracts import AcquireRequest, AcquiredAsset, ReadableRequest, ReadableDocument
from .discovery import check_asset


def acquire_material(req: AcquireRequest, invocation, transport: HttpTransport | None, *, identity_profile):
    spec = family(req.asset.family_id)
    check_asset(req.asset, spec, identity_profile)
    if type(req.max_bytes) is not int or not 0 < req.max_bytes <= 64 * 1024 * 1024:
        raise ValueError("minfin.acquisition_size_invalid")
    if type(req.deadline_seconds) is not int or not 1 <= req.deadline_seconds <= 600:
        raise ValueError("minfin.acquisition_deadline_invalid")
    request = file_request(req.asset.url, limit=req.max_bytes, deadline=req.deadline_seconds)
    invocation.stage("download_asset")
    original = receive_source(request, transport=invocation.provider("http", transport),
                              source_id=req.asset.source_id, invocation=invocation,
                              media_types=FILE_MIMES, retry=RetryPolicy(),
                              default_media_type="application/octet-stream")
    content = original.payload.data
    fmt = req.asset.format
    if fmt in {"xlsx", "xlsm", "zip", "docx"} and not content.startswith(b"PK"):
        raise OperationFailure("minfin.asset_envelope_invalid")
    if fmt in {"xls", "doc"} and not content.startswith(b"\xd0\xcf\x11\xe0"):
        raise OperationFailure("minfin.asset_envelope_invalid")
    if fmt == "pdf" and not content.startswith(b"%PDF-"):
        raise OperationFailure("minfin.asset_envelope_invalid")
    if fmt == "csv" and (b"<html" in content[:2048].lower() or b"<body" in content[:2048].lower()):
        raise OperationFailure("minfin.asset_envelope_invalid")
    return AcquiredAsset(req.asset, original)



def read_document(req: ReadableRequest, invocation):
    from stratbox.core.formats.documents import extract_document
    spec = family(req.family_id)
    if type(req.max_pages) is not int or not 1 <= req.max_pages <= 250:
        raise OperationFailure("minfin.pdf_page_limit_invalid")
    if req.format not in {"pdf", "docx"}:
        raise OperationFailure("minfin.readable_format_unsupported")
    use_payload(req.payload, invocation, role="publisher_document", limit=64 * 1024 * 1024)
    source_id = req.payload.source_id or spec.default_source_id
    if source_id not in {spec.default_source_id, *(item.source_id for item in spec.series)}:
        raise ValueError("minfin.source_family_mismatch")
    publication = req.publication
    if publication is not None and publication.series_id != source_id:
        raise ValueError("minfin.publication_source_mismatch")
    document = extract_document(req.payload, series_id=source_id,
        issue_id=publication.issue_id if publication is not None else "unidentified",
        asset_id=publication.asset_id if publication is not None else "supplied",
        profile_id="minfin.document.blocks", budget=invocation.budget, checkpoint=invocation.check_cancelled,
        max_pages=req.max_pages)
    if document.format != req.format:
        raise ValueError("minfin.document_format_mismatch")
    if document.format == "pdf" and len(document.blocks) > req.max_pages:
        raise OperationFailure("minfin.pdf_inaccessible_or_oversized")
    pages = tuple(block.text if block.kind != "table" else "\n".join(" | ".join(row) for row in block.rows)
                  for block in document.blocks)
    invocation.account_output(document.identity)
    invocation.record(document.identity)
    return Completion(ReadableDocument(req.family_id, req.payload.identity, pages,
                      document=document, publication=publication), "partial", "minfin.readable_text_only")
