"""Independent Minfin operations over trusted domain contracts and source bytes."""
from __future__ import annotations

from dataclasses import asdict, replace
from urllib.parse import unquote, urlsplit

from stratbox.core.execution import ExecutionContext, OperationFailure, run
from stratbox.core.network import HttpTransport, RetryPolicy
from stratbox.core.runtime.capabilities import ProviderSelection
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
    SerializeFlakeRequest, ReadFlakeRequest, FlakeSnapshotRequest, ReadFlakeSnapshotRequest,
)
from ..analytics.contracts import SummaryRequest, NoticeRequest, NoticePreparation
from .contracts import CaptureRequest, CaptureResult
from ..publications.catalog import family
from ..publications.context import context_for
from ..publications.access import PAGE_MIMES, page_request, allowed_page
from ..publications.discovery import discover_links, enrich_index, identify_index
from ..tables.extraction import compare_tables, extract_tables, validate_tables
from ..tables.mapping import map_metrics
from ..tables.representation import render_csv, serialize_tables, read_serialized_tables, render_flake_csv
from ..tables.cleaning import build_flake
from ..tables.flake_codec import serialize_flake, read_flake
from ..tables.snapshots import flake_snapshot, flake_from_snapshot
from .lineage import use_extract, use_flake, use_representation, record_representation, record_value
from ..analytics.indicators import summarize
from ..analytics.notices import prepare_notification
from ..publications.updates import assess_updates
from ..publications.materials import acquire_material, read_document
from .bindings import bind_family, bind_series


def _error(error: Exception, fallback: str = "minfin.source_invalid") -> OperationFailure:
    code = str(error)
    if code.startswith(("minfin.", "workbook.", "archive.")) and len(code) < 95 and all(
        c.isalnum() or c in "_." for c in code
    ):
        return OperationFailure(code)
    return OperationFailure(fallback)


def discover(request: DiscoverRequest, *, transport: HttpTransport | None = None,
             selection: ProviderSelection | None = None, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            bound = bind_family(req.family_id)
            spec = bound.source
            source = req.index
            page_url = req.page_url if req.page_url is not None else bound.acquisition.landing_url
            if not allowed_page(page_url):
                raise ValueError("minfin.page_forbidden")
            if source is None:
                invocation.stage("download_landing_page")
                result = receive_source(
                    page_request(page_url),
                    transport=invocation.provider("http", transport),
                    source_id=spec.family_id + ".index", invocation=invocation,
                    media_types=PAGE_MIMES, retry=RetryPolicy(),
                )
                source = result.payload
            invocation.stage("parse_landing_page")
            use_payload(source, invocation, role="publisher_index", limit=8 * 1024 * 1024)
            text = source.data.decode(source.charset or "utf-8", errors="strict")
            return identify_index(enrich_index(discover_links(spec, source, req.max_links, page_url=page_url),
                                               text, page_url, profile=bound.publication),
                                  spec, bound.identification)
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.DISCOVER, request, work, context=context, providers={"http": transport},
               provider_selections={} if selection is None else {"http": selection})


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
        return acquire_material(req, invocation, transport,
                                identity_profile=bind_family(req.asset.family_id).identification)
    except ValueError as exc:
        raise _error(exc) from None

def acquire(request: AcquireRequest, *, transport: HttpTransport | None = None,
            selection: ProviderSelection | None = None, context: ExecutionContext | None = None):
    return run(D.ACQUIRE, request, lambda req, invocation: _acquire(req, invocation, transport),
               context=context, providers={"http": transport},
               provider_selections={} if selection is None else {"http": selection})


def _extract(req: ExtractRequest, invocation):
    invocation.stage("extract_source_cells")
    use_payload(req.payload, invocation, role="publisher_material", limit=64 * 1024 * 1024)
    try:
        bound = bind_family(req.family_id)
        sources = frozenset((bound.source.default_source_id,
                             *(s.source_id for s in bound.source.series if s.kind == "table")))
        value = extract_tables(req, invocation, allowed_sources=sources,
                               allowed_formats=frozenset({"xlsx", "xls", "xlsm", "csv", "zip"}))
        record_representation(invocation, serialize_tables(SerializeRequest(value)), parameters={
            "family_id": req.family_id, "format": req.format, "member": req.member,
            "selected_sheets": req.selected_sheets, "csv_encoding": req.csv_encoding,
        })
        return value
    except ValueError as exc:
        raise _error(exc, "minfin.table_invalid") from None


def extract(request: ExtractRequest, *, context: ExecutionContext | None = None):
    return run(D.EXTRACT, request, _extract, context=context)


def capture(request: CaptureRequest, *, transport: HttpTransport | None = None,
            selection: ProviderSelection | None = None, context: ExecutionContext | None = None):
    def work(req, invocation):
        acquired = _acquire(AcquireRequest(req.asset, req.max_bytes), invocation, transport)
        if req.asset.format == "pdf":
            raise OperationFailure("minfin.pdf_requires_readable_operation")
        value = _extract(ExtractRequest(req.asset.family_id, acquired.source.payload, req.asset.format,
                                        req.member, req.selected_sheets, req.max_cells,
                                        publication=context_for(req.asset)), invocation)
        return CaptureResult(acquired, value)
    return run(D.CAPTURE, request, work, context=context, providers={"http": transport},
               provider_selections={} if selection is None else {"http": selection})


def validate(request: ValidateRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            bound = bind_family(req.extract.family_id)
            if req.extract.source_id not in {
                bound.source.default_source_id,
                *(s.source_id for s in bound.source.series if s.kind == "table"),
            }:
                raise ValueError("minfin.source_family_mismatch")
            use_extract(invocation, req.extract)
            value = validate_tables(req)
            record_value(invocation, value, schema="minfin.structural_validation.v1")
            return value
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.VALIDATE, request, work, context=context)


def compare(request: CompareRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            use_extract(invocation, req.before, role="before")
            use_extract(invocation, req.after, role="after")
            value = compare_tables(req)
            record_value(invocation, value, schema="minfin.source_cell_delta.v1",
                         parameters={"max_changes": req.max_changes})
            return value
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.COMPARE, request, work, context=context)


def map_observations(request: MapRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            use_extract(invocation, req.extract)
            value = map_metrics(req)
            record_value(invocation, value, schema="minfin.mapped_observations.v1",
                         parameters={"bindings": [asdict(binding) for binding in req.bindings]})
            return value
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.MAP, request, work, context=context)


def render_csv_cells(request: RenderRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            use_extract(invocation, req.extract)
            value = render_csv(req)
            record_representation(invocation, value)
            return value
        except ValueError as exc:
            raise _error(exc, "minfin.representation_invalid") from None
    return run(D.RENDER, request, work, context=context)


def readable_document(request: ReadableRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return read_document(req, invocation)
        except ValueError as exc:
            raise _error(exc) from None
    return run(D.READABLE, request, work, context=context)

def serialize_extract(request: SerializeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            bound = bind_family(req.extract.family_id)
            if req.extract.source_id not in {
                bound.source.default_source_id,
                *(s.source_id for s in bound.source.series if s.kind == "table"),
            }:
                raise ValueError("minfin.source_family_mismatch")
            value = use_extract(invocation, req.extract)
            record_representation(invocation, value)
            return value
        except ValueError as exc:
            raise _error(exc, "minfin.representation_invalid") from None
    return run(D.SERIALIZE, request, work, context=context)


def read_representation(request: ReadRepresentationRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            use_representation(invocation, req.representation, role="representation")
            value = read_serialized_tables(req)
            bound = bind_family(value.family_id)
            if value.source_id not in {
                bound.source.default_source_id,
                *(s.source_id for s in bound.source.series if s.kind == "table"),
            }:
                raise ValueError("minfin.representation_invalid")
            invocation.budget.charge("cells", sum(len(sheet.cells) for sheet in value.sheets))
            record_representation(invocation, serialize_tables(SerializeRequest(value)))
            return value
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
            bound = bind_family(req.index.family_id)
            asset_ids = {s.source_id: bound.identification.rule(s.slot).asset_id
                         for s in bound.source.series}
            versions = {s.source_id: bind_series(req.index.family_id, s.source_id).method_version
                        for s in bound.source.series if s.kind == "table"}
            return assess_updates(req, source=bound.source, asset_ids=asset_ids,
                                  method_versions=versions)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.PLAN_UPDATES, request, work, context=context)


def build_source_flake(request: BuildFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("clean_source_table")
        try:
            bound = bind_series(req.extract.family_id, req.source_id)
            if bound.table is None:
                raise ValueError("minfin.flake.source_unsupported")
            use_extract(invocation, req.extract)
            value = build_flake(req, profile=bound.table,
                                frequency=bound.series.periodicity, basis=bound.series.basis)
            record_representation(invocation, serialize_flake(SerializeFlakeRequest(value)),
                                  parameters={"source_id": req.source_id, "selected_sheet": req.selected_sheet},
                                  resources={"table_profile": bound.table.profile_id,
                                             "table_method": bound.table.method_version})
            return value
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.BUILD_FLAKE, request, work, context=context)


def render_source_flake(request: RenderFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            use_flake(invocation, req.flake)
            value = render_flake_csv(req)
            record_representation(invocation, value)
            return value
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.RENDER_FLAKE, request, work, context=context)



def serialize_source_flake(request: SerializeFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            bound = bind_series(req.flake.family_id, req.flake.source_id)
            if bound.table is None:
                raise ValueError("minfin.flake.source_unsupported")
            value = use_flake(invocation, req.flake)
            record_representation(invocation, value)
            return value
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.SERIALIZE_FLAKE, request, work, context=context)


def read_source_flake(request: ReadFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            use_representation(invocation, req.representation, role="representation")
            value = read_flake(req)
            bound = bind_series(value.family_id, value.source_id)
            if bound.table is None:
                raise ValueError("minfin.flake.source_unsupported")
            invocation.budget.charge("cells", len(value.rows) * len(value.columns))
            record_representation(invocation, serialize_flake(SerializeFlakeRequest(value)))
            return value
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.READ_FLAKE, request, work, context=context)


def build_flake_snapshot(request: FlakeSnapshotRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            bound = bind_series(req.flake.family_id, req.flake.source_id)
            if bound.table is None:
                raise ValueError("minfin.flake.source_unsupported")
            use_flake(invocation, req.flake)
            value = flake_snapshot(req.flake, dataset_id=req.dataset_id, version_id=req.version_id,
                                   inputs=tuple(invocation.used_inputs))
            for name, table in value.tables:
                invocation.account_output(table.identity, key=f"snapshot:{name}")
            invocation.account_output(value.identity, key="snapshot:manifest")
            invocation.record(value.identity, parameters={"dataset_id": req.dataset_id, "version_id": req.version_id})
            return value
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.FLAKE_SNAPSHOT, request, work, context=context)


def read_flake_snapshot(request: ReadFlakeSnapshotRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            value = flake_from_snapshot(req.snapshot)
            bound = bind_series(value.family_id, value.source_id)
            if bound.table is None:
                raise ValueError("minfin.flake.source_unsupported")
            invocation.budget.charge("input_bytes", req.snapshot.identity.size +
                                     sum(table.identity.size for _, table in req.snapshot.tables))
            invocation.budget.charge("cells", sum(len(table.rows) * len(table.schema.columns)
                                                 for _, table in req.snapshot.tables))
            invocation.use(UsedInputReceipt("snapshot", req.snapshot.identity,
                "application/vnd.stratbox.dataset+json", "inline", value.source_id))
            record_representation(invocation, serialize_flake(SerializeFlakeRequest(value)))
            return value
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.READ_FLAKE_SNAPSHOT, request, work, context=context)

def calculate_headlines(request: SummaryRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("calculate_source_headlines")
        try:
            bound = bind_series(req.flake.family_id, req.flake.source_id)
            if bound.metrics is None or bound.table is None:
                raise ValueError("minfin.summary.source_unsupported")
            if (req.flake.method_version != bound.table.method_version or
                req.flake.frequency != bound.series.periodicity or
                req.flake.value_basis != bound.series.basis):
                raise ValueError("minfin.summary.profile_mismatch")
            use_flake(invocation, req.flake)
            value = summarize(req, bound.metrics)
            record_value(invocation, value, schema="minfin.headlines.v1",
                         parameters={"period_id": req.period_id},
                         resources={"metrics_profile": bound.metrics.profile_id,
                                    "metrics_method": str(bound.metrics.method_version)})
            return value
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
    "serialize_source_flake", "read_source_flake", "build_flake_snapshot", "read_flake_snapshot",
    "prepare_notice_facts",
)
