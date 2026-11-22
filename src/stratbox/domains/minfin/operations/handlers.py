"""Independent Minfin operations over trusted domain contracts and source bytes."""
from __future__ import annotations

from dataclasses import replace
from urllib.parse import unquote, urlsplit

from stratbox.core.execution import ExecutionContext, OperationFailure, run
from stratbox.core.network import HttpTransport, RetryPolicy
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.validation import use_payload
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

from . import definitions as D
from ..publications.contracts import (
    AcquireRequest, AcquiredAsset, DiscoverRequest, InspectRequest, Inspection,
    ReadableDocument, ReadableRequest, UpdateRequest,
)
from ..tables.contracts import (
    CompareRequest, ExtractRequest, MapRequest, RenderRequest, ValidateRequest,
    SerializeRequest, ReadRepresentationRequest, BuildFlakeRequest, RenderFlakeRequest,
)
from ..analytics.contracts import SummaryRequest, NoticeRequest, NoticePreparation
from .contracts import CaptureRequest, CaptureResult
from ..publications.catalog import family
from ..publications.access import PAGE_MIMES, page_request
from ..publications.discovery import discover_links
from ..tables.extraction import compare_tables, extract_tables, validate_tables
from ..tables.mapping import map_metrics
from ..tables.representation import render_csv, serialize_tables, read_serialized_tables, render_flake_csv
from ..tables.cleaning import build_flake
from ..analytics.indicators import summarize
from ..analytics.notices import prepare_notification
from ..publications.updates import assess_updates
from ..publications.materials import acquire_material, read_document


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
            from ..publications.discovery import enrich_index
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
        return acquire_material(req, invocation, transport)
    except ValueError as exc:
        raise _error(exc) from None

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
        try:
            return read_document(req, invocation)
        except ValueError as exc:
            raise _error(exc) from None
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


# Publisher-marker, clean-flake and channel-neutral analytics operations.

def _wrap_error(exc: ValueError):
    code = str(exc)
    if code.startswith("minfin.") and len(code) <= 95 and all(c.isalnum() or c in "_." for c in code):
        raise OperationFailure(code) from None
    raise OperationFailure("minfin.pipeline_invalid") from None


def plan_updates(request: UpdateRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("assess_publisher_markers")
        try:
            return assess_updates(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.PLAN_UPDATES, request, work, context=context)


def build_source_flake(request: BuildFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("clean_source_table")
        try:
            return build_flake(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.BUILD_FLAKE, request, work, context=context)


def render_source_flake(request: RenderFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return render_flake_csv(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.RENDER_FLAKE, request, work, context=context)


def calculate_headlines(request: SummaryRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("calculate_source_headlines")
        try:
            return summarize(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.SUMMARIZE, request, work, context=context)


def prepare_notice_facts(request: NoticeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("qualify_notification_candidate")
        try:
            facts, reason = prepare_notification(req)
        except ValueError as exc:
            _wrap_error(exc)
        return NoticePreparation("ready" if facts is not None else "skipped", facts, reason)
    return run(D.PREPARE_NOTICE, request, work, context=context)


__all__ = (
    "discover", "inspect", "acquire", "capture", "extract", "validate", "compare",
    "map_observations", "render_csv_cells", "readable_document",
    "serialize_extract", "read_representation", "plan_updates",
    "build_source_flake", "render_source_flake", "calculate_headlines",
    "prepare_notice_facts",
)
