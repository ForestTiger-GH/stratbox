"""Independent Minfin operations over trusted domain contracts and source bytes."""
from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from urllib.parse import unquote, urlsplit

from stratbox.core.execution import Completion, ExecutionContext, OperationFailure, run
from stratbox.core.network import HttpTransport, RetryPolicy
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.validation import use_payload
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

from . import definitions as D
from .models import (
    AcquireRequest, AcquiredAsset, CaptureRequest, CaptureResult, CompareRequest,
    DiscoverRequest, InspectRequest, Inspection, MapRequest, ReadableDocument,
    ReadableRequest, RenderRequest, ExtractRequest, ValidateRequest, SerializeRequest,
    ReadRepresentationRequest,
)
from .registry import family
from .source import FILE_MIMES, PAGE_MIMES, check_asset, discover_links, file_request, page_request
from .tables import compare_tables, extract_tables, map_metrics, render_csv, validate_tables, serialize_tables, read_serialized_tables


def _error(error: Exception, fallback: str = "minfin.source_invalid") -> OperationFailure:
    code = str(error)
    if code.startswith(("minfin.", "workbook.", "archive.")) and len(code) < 95 and all(
        c.isalnum() or c in "_." for c in code
    ):
        return OperationFailure(code)
    return OperationFailure(fallback)


def discover(request: DiscoverRequest, *, transport: HttpTransport | None = None,
             context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            spec = family(req.family_id)
            source = req.index
            if source is None:
                invocation.stage("download_landing_page")
                result = receive_source(
                    page_request(spec.landing_url),
                    transport=invocation.provider("http", transport),
                    source_id=spec.family_id + ".index", invocation=invocation,
                    media_types=PAGE_MIMES, retry=RetryPolicy(),
                )
                source = result.payload
            invocation.stage("parse_landing_page")
            use_payload(source, invocation, role="publisher_index", limit=8 * 1024 * 1024)
            from .publication_adapter import enrich_index
            text = source.data.decode(source.charset or "utf-8", errors="strict")
            return enrich_index(discover_links(spec, source, req.max_links), text, spec.landing_url)
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.DISCOVER, request, work, context=context, providers={"http": transport})


def inspect(request: InspectRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        if req.before.family_id != req.after.family_id:
            raise OperationFailure("minfin.index_mismatch")
        old = {a.url for a in req.before.assets}
        new = {a.url for a in req.after.assets}
        return Inspection(req.after.family_id, tuple(sorted(new - old)), tuple(sorted(old - new)))
    return run(D.INSPECT, request, work, context=context)


def _acquire(req: AcquireRequest, invocation, transport: HttpTransport | None):
    try:
        spec = family(req.asset.family_id)
        check_asset(req.asset, spec)
        if type(req.max_bytes) is not int or not 0 < req.max_bytes <= 64 * 1024 * 1024:
            raise ValueError("minfin.acquisition_size_invalid")
        if type(req.deadline_seconds) is not int or not 1 <= req.deadline_seconds <= 600:
            raise ValueError("minfin.acquisition_deadline_invalid")
        request = file_request(req.asset.url, limit=req.max_bytes, deadline=req.deadline_seconds)
    except ValueError as exc:
        raise _error(exc) from None
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


def acquire(request: AcquireRequest, *, transport: HttpTransport | None = None,
            context: ExecutionContext | None = None):
    return run(D.ACQUIRE, request, lambda req, invocation: _acquire(req, invocation, transport),
               context=context, providers={"http": transport})


def _extract(req: ExtractRequest, invocation):
    invocation.stage("extract_source_cells")
    use_payload(req.payload, invocation, role="publisher_material", limit=64 * 1024 * 1024)
    try:
        return extract_tables(req, invocation)
    except ValueError as exc:
        raise _error(exc, "minfin.table_invalid") from None


def extract(request: ExtractRequest, *, context: ExecutionContext | None = None):
    return run(D.EXTRACT, request, _extract, context=context)


def capture(request: CaptureRequest, *, transport: HttpTransport | None = None,
            context: ExecutionContext | None = None):
    def work(req, invocation):
        acquired = _acquire(AcquireRequest(req.asset, req.max_bytes), invocation, transport)
        if req.asset.format == "pdf":
            raise OperationFailure("minfin.pdf_requires_readable_operation")
        value = _extract(ExtractRequest(req.asset.family_id, acquired.source.payload, req.asset.format,
                                        req.member, req.selected_sheets, req.max_cells), invocation)
        return CaptureResult(acquired, value)
    return run(D.CAPTURE, request, work, context=context, providers={"http": transport})


def validate(request: ValidateRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return validate_tables(req)
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.VALIDATE, request, work, context=context)


def compare(request: CompareRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return compare_tables(req)
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.COMPARE, request, work, context=context)


def map_observations(request: MapRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return map_metrics(req)
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.MAP, request, work, context=context)


def render_csv_cells(request: RenderRequest, *, context: ExecutionContext | None = None):
    return run(D.RENDER, request, lambda req, invocation: render_csv(req), context=context)


def readable_document(request: ReadableRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        from stratbox.core.runtime.dependencies import require_extra
        try:
            family(req.family_id)
        except ValueError as exc:
            raise _error(exc) from None
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
    return run(D.READABLE, request, work, context=context)


def serialize_extract(request: SerializeRequest, *, context: ExecutionContext | None = None):
    return run(D.SERIALIZE, request, lambda req, invocation: serialize_tables(req), context=context)


def read_representation(request: ReadRepresentationRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return read_serialized_tables(req)
        except ValueError as exc:
            raise _error(exc, "minfin.representation_invalid") from None
    return run(D.READ_EXTRACT, request, work, context=context)


__all__ = ("discover", "inspect", "acquire", "capture", "extract", "validate", "compare",
           "map_observations", "render_csv_cells", "readable_document", "serialize_extract", "read_representation")