"""Publisher-material admission and optional readable document conversion.

These are source-specific actions invoked from registered operation handlers.
The domain never owns HTTP transports, storage effects, or message delivery.
"""
from __future__ import annotations
from io import BytesIO
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
    from stratbox.core.runtime.dependencies import require_extra
    family(req.family_id)
    if type(req.max_pages) is not int or not 1 <= req.max_pages <= 250:
        raise OperationFailure("minfin.pdf_page_limit_invalid")
    use_payload(req.payload, invocation, role="publisher_pdf", limit=64 * 1024 * 1024)
    if req.format == "pdf":
        if not req.payload.data.startswith(b"%PDF-"):
            raise OperationFailure("minfin.pdf_envelope_invalid")
        pypdf = require_extra("pypdf", "pdf")
        try:
            reader = pypdf.PdfReader(BytesIO(req.payload.data), strict=True)
            if reader.is_encrypted or len(reader.pages) > req.max_pages:
                raise OperationFailure("minfin.pdf_inaccessible_or_oversized")
            pages = tuple(page.extract_text() or "" for page in reader.pages)
        except OperationFailure:
            raise
        except Exception:
            raise OperationFailure("minfin.pdf_parse_failed") from None
    elif req.format == "docx":
        if not req.payload.data.startswith(b"PK"):
            raise OperationFailure("minfin.docx_envelope_invalid")
        docx = require_extra("docx", "documents")
        try:
            # Bound document ZIP before the third-party XML parser sees it.
            from stratbox.core.formats.archives.members import ArchiveLimits, open_zip
            with open_zip(req.payload.data, ArchiveLimits(1000, 80_000_000, 16_000_000, 64_000_000)) as package:
                if "word/document.xml" not in package.namelist():
                    raise OperationFailure("minfin.docx_invalid")
            document = docx.Document(BytesIO(req.payload.data))
            blocks = [p.text for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    blocks.append(" | ".join(cell.text.replace("\n", " ") for cell in row.cells))
            if sum(len(block) for block in blocks) > 5_000_000:
                raise OperationFailure("minfin.readable_text_limit")
            pages = tuple(blocks[:20_000])
        except OperationFailure:
            raise
        except Exception:
            raise OperationFailure("minfin.docx_parse_failed") from None
    else:
        raise OperationFailure("minfin.readable_format_unsupported")
    return Completion(ReadableDocument(req.family_id, req.payload.identity, pages),
                      "partial", "minfin.readable_text_only")
