"""Fiscal command leaves over pure algorithms and explicit provider contracts."""
from __future__ import annotations

from dataclasses import replace

from stratbox.core.execution.contracts import OperationFailure
from stratbox.core.execution import values
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


def _snapshot(value, invocation):
    from .documents.contracts import PublisherDocument
    if isinstance(value, PublisherDocument):
        from .documents.snapshots import snapshot_document
        return snapshot_document(value)


def _tracked(request, invocation, build, *, inputs=()):
    try:
        for name in inputs:
            if request.get(name) is not None:
                values.use_value(request[name], invocation, name, snapshot_factory=_snapshot, charge_cells=False)
        result = build()
        _admit(result)
        values.account_value(result, invocation, snapshot_factory=_snapshot, charge_cells=False)
        return result
    except (ValueError, TypeError, KeyError) as error:
        code = str(error)
        if not code.startswith(("minfin.", "document.", "view.", "observations.", "workbook.")) or len(code)>95 or not all(c.isalnum() or c in "_." for c in code):
            code = "minfin.command_invalid"
        raise OperationFailure(code) from None


def _admit(value):
    """Replayed values retain the same registered source admission as fresh work."""
    from .tables.contracts import TableExtract, FlakeTable
    from .publications.catalog import family
    from .tables.profiles import table_profile
    if isinstance(value, TableExtract):
        source = family(value.family_id)
        if value.source_id not in {source.default_source_id, *(s.source_id for s in source.series if s.kind == "table")}:
            raise ValueError("minfin.source_family_mismatch")
    if isinstance(value, FlakeTable):
        source = family(value.family_id)
        series = source.source(value.source_id)
        shape = table_profile(source.profiles.table)
        if (series.kind != "table" or value.frequency != series.periodicity or value.value_basis != series.basis
                or value.method_version != shape.method_version or value.unit_hint != shape.unit_hint):
            raise ValueError("minfin.flake.profile_mismatch")


def discover(request, invocation):
    def build():
        from .publications.catalog import family
        from .publications.access import allowed_page
        from .publications.profiles import acquisition_profile, identification_profile, publication_profile
        from .publications.discovery import discover_links, enrich_index, identify_index
        source = family(request["family_id"])
        page_url = request["page_url"] or acquisition_profile(source.profiles.acquisition).landing_url
        if not allowed_page(page_url):
            raise ValueError("minfin.page_forbidden")
        payload = request["index"]
        text = payload.data.decode(payload.charset or "utf-8", errors="strict")
        return identify_index(enrich_index(discover_links(source, payload, request["max_links"], page_url=page_url),
            text, page_url, profile=publication_profile(source.profiles.discovery)), source,
            identification_profile(source.profiles.identification))
    return _tracked(request, invocation, build, inputs=("index",))


def inspect(request, invocation):
    def build():
        from .publications.contracts import Inspection
        before, after = request["before"], request["after"]
        if before.family_id != after.family_id:
            raise ValueError("minfin.index_mismatch")
        old, new = {a.url for a in before.assets}, {a.url for a in after.assets}
        return Inspection(after.family_id, tuple(sorted(new-old)), tuple(sorted(old-new)))
    return _tracked(request, invocation, build, inputs=("before", "after"))


def acquire(request, invocation):
    def build():
        from .publications.contracts import AcquireRequest
        from .publications.materials import acquire_material
        from .publications.catalog import family
        from .publications.profiles import identification_profile
        source = family(request["asset"].family_id)
        return acquire_material(AcquireRequest(**request), invocation, None,
            identity_profile=identification_profile(source.profiles.identification))
    return _tracked(request, invocation, build)


def asset_payload(request, invocation):
    return _tracked(request, invocation, lambda: request["acquired"].source.payload)


def asset_context(request, invocation):
    from .publications.context import context_for
    asset = request["acquired"].asset
    return {"publication": context_for(asset), "family_id": asset.family_id, "format": asset.format}


def extract(request, invocation):
    def build():
        from .publications.catalog import family
        from .tables.contracts import ExtractRequest
        from .tables.extraction import extract_tables
        source = family(request["family_id"])
        return extract_tables(ExtractRequest(**request), invocation,
            allowed_sources=frozenset((source.default_source_id, *(s.source_id for s in source.series if s.kind=="table"))),
            allowed_formats=frozenset({"xlsx", "xls", "xlsm", "csv", "zip"}))
    return _tracked(request, invocation, build, inputs=("payload",))


def build_flake(request, invocation):
    def build():
        from .publications.catalog import family
        from .tables.profiles import TableProfile, table_profile
        from .tables.cleaning import build_flake as interpret
        from .tables.contracts import BuildFlakeRequest
        source = family(request["extract"].family_id)
        series = source.source(request["source_id"])
        if series.kind != "table":
            raise ValueError("minfin.flake.source_unsupported")
        parameters = dict(request)
        profile = parameters.pop("profile")
        shape = table_profile(source.profiles.table)
        if profile is not None:
            if (profile.get("source_id",series.source_id) != series.source_id
                    or profile.get("frequency",series.periodicity) != series.periodicity
                    or profile.get("value_basis",series.basis) != series.basis):
                raise ValueError("minfin.flake.profile_mismatch")
            shape = table_profile(profile.get("table_profile",source.profiles.table))
            if profile.get("layout") is not None:
                shape = TableProfile(**dict(profile["layout"]))
        return interpret(BuildFlakeRequest(**parameters), profile=shape,
            frequency=series.periodicity, basis=series.basis)
    return _tracked(request, invocation, build, inputs=("extract",))


def summarize(request, invocation):
    def build():
        from .publications.catalog import family
        from .tables.profiles import table_profile
        from .analytics.profiles import headline_profile
        from .analytics.contracts import SummaryRequest
        from .analytics.indicators import summarize as calculate
        flake = request["flake"]
        source = family(flake.family_id)
        series = source.source(flake.source_id)
        shape = table_profile(source.profiles.table)
        if flake.method_version != shape.method_version or flake.frequency != series.periodicity or flake.value_basis != series.basis:
            raise ValueError("minfin.summary.profile_mismatch")
        return calculate(SummaryRequest(**request), headline_profile(source.profiles.metrics))
    return _tracked(request, invocation, build, inputs=("flake",))


def plan_updates(request, invocation):
    def build():
        from .publications.catalog import family
        from .publications.profiles import identification_profile
        from .tables.profiles import table_profile
        from .publications.contracts import UpdateRequest
        from .publications.updates import assess_updates
        source = family(request["index"].family_id)
        identity = identification_profile(source.profiles.identification)
        versions = {s.source_id: table_profile(source.profiles.table).method_version for s in source.series if s.kind=="table"}
        return assess_updates(UpdateRequest(**request), source=source,
            asset_ids={s.source_id: identity.rule(s.slot).asset_id for s in source.series}, method_versions=versions)
    return _tracked(request, invocation, build, inputs=("index",))


def prepare_notice(request, invocation):
    def build():
        from .analytics.contracts import NoticeRequest, NoticePreparation
        from .analytics.notices import prepare_notification
        facts, reason = prepare_notification(NoticeRequest(**request))
        return NoticePreparation("ready" if facts is not None else "skipped", facts, reason)
    return _tracked(request, invocation, build, inputs=("summary",))


def extract_document(request, invocation):
    def build():
        from stratbox.core.formats.documents import extract_document as decode
        from .publications.catalog import family
        from .documents.contracts import PublisherDocument
        publication = request["publication"]
        series = family(request["family_id"]).source(publication.series_id)
        if series.kind != "document" or request["payload"].source_id not in {None, series.source_id}:
            raise ValueError("minfin.document.source_mismatch")
        document = decode(request["payload"], series_id=series.source_id, issue_id=publication.issue_id,
            asset_id=publication.asset_id, profile_id="minfin.document.blocks", budget=invocation.budget,
            checkpoint=invocation.check_cancelled, max_pages=request["max_pages"])
        return PublisherDocument(request["family_id"], document, publication)
    return _tracked(request, invocation, build, inputs=("payload",))


def convert_document(request, invocation):
    from .documents.conversion import convert_legacy_document
    return _tracked(request, invocation, lambda: convert_legacy_document(request["payload"],
        invocation.provider("document_converter"), max_bytes=request["max_bytes"], checkpoint=invocation.check_cancelled), inputs=("payload",))


def decode_converted_document(request, invocation):
    from .documents.conversion import ConvertedDocument
    converted = request["converted"]
    if not isinstance(converted, ConvertedDocument):
        raise OperationFailure("minfin.document.conversion_required")
    value = extract_document({"payload": converted.payload, "family_id": request["family_id"],
        "publication": request["publication"], "max_pages": request["max_pages"]}, invocation)
    original = UsedInputReceipt("publisher_original", converted.original_identity, "application/msword", "reference_only", converted.payload.source_id)
    invocation.use(original)
    document = replace(value.document, lineage=(*value.document.lineage, original),
        qualifications=(*value.document.qualifications, "Conversion provider: "+converted.provider_id+"@"+converted.provider_revision,
                        "Legacy DOC original identity is distinct from converted DOCX decoding identity."))
    return replace(value, document=document)


def document_observations(request, invocation):
    from .integration.document_observations import interpret_document
    return _tracked(request, invocation, lambda: interpret_document(request["document"], request["profile"],
        dataset_id=request["dataset_id"], release_id=request["release_id"]), inputs=("document",))


def validate_document(request, invocation):
    from .documents.validation import validate_document as validate
    return _tracked(request,invocation,lambda:validate(request["document"]),inputs=("document",))




def validate(request, invocation):
    from .tables.contracts import ValidateRequest
    from .tables.extraction import validate_tables as build
    return _tracked(request, invocation, lambda: build(ValidateRequest(**request)), inputs=('extract',))


def compare(request, invocation):
    from .tables.contracts import CompareRequest
    from .tables.extraction import compare_tables as build
    return _tracked(request, invocation, lambda: build(CompareRequest(**request)), inputs=('before', 'after'))


def map_observations(request, invocation):
    from .tables.contracts import MapRequest
    from .tables.mapping import map_metrics as build
    return _tracked(request, invocation, lambda: build(MapRequest(**request)), inputs=('extract',))


def render_csv(request, invocation):
    from .tables.contracts import RenderRequest
    from .tables.representation import render_csv as build
    return _tracked(request, invocation, lambda: build(RenderRequest(**request)), inputs=('extract',))


def serialize(request, invocation):
    from .tables.contracts import SerializeRequest
    from .tables.representation import serialize_tables as build
    return _tracked(request, invocation, lambda: build(SerializeRequest(**request)), inputs=('extract',))


def read_representation(request, invocation):
    from .tables.contracts import ReadRepresentationRequest
    from .tables.representation import read_serialized_tables as build
    return _tracked(request, invocation, lambda: build(ReadRepresentationRequest(**request)), inputs=('representation',))


def render_flake(request, invocation):
    from .tables.contracts import RenderFlakeRequest
    from .tables.representation import render_flake_csv as build
    return _tracked(request, invocation, lambda: build(RenderFlakeRequest(**request)), inputs=('flake',))


def serialize_flake(request, invocation):
    from .tables.contracts import SerializeFlakeRequest
    from .tables.flake_codec import serialize_flake as build
    return _tracked(request, invocation, lambda: build(SerializeFlakeRequest(**request)), inputs=('flake',))


def read_flake(request, invocation):
    from .tables.contracts import ReadFlakeRequest
    from .tables.flake_codec import read_flake as build
    return _tracked(request, invocation, lambda: build(ReadFlakeRequest(**request)), inputs=('representation',))


def integrate(request, invocation):
    from .integration.contracts import IntegrateRequest
    from .integration.observations import integrate as build
    return _tracked(request, invocation, lambda: build(IntegrateRequest(**request)), inputs=('flake',))


def prepare_view(request, invocation):
    from .products.contracts import PrepareHeadlineViewRequest
    from .products.views import prepare_view as build
    return _tracked(request, invocation, lambda: build(PrepareHeadlineViewRequest(**request)), inputs=('summary',))


def flake_snapshot(request, invocation):
    from stratbox.domains.minfin.tables.snapshots import flake_snapshot as build
    return _tracked(request, invocation, lambda: build(request['flake'], dataset_id=request["dataset_id"], version_id=request["version_id"]), inputs=('flake',))


def read_flake_snapshot(request, invocation):
    from stratbox.domains.minfin.tables.snapshots import flake_from_snapshot as build
    return _tracked(request, invocation, lambda: build(request['snapshot']), inputs=('snapshot',))


def observation_snapshot(request, invocation):
    from stratbox.shared.data.observation_snapshots import observation_snapshot as build
    return _tracked(request, invocation, lambda: build(request['batch'], dataset_id=request["dataset_id"], version_id=request["version_id"]), inputs=('batch',))


def read_observations(request, invocation):
    from stratbox.shared.data.observation_snapshots import observations_from_snapshot as build
    return _tracked(request, invocation, lambda: build(request['snapshot']), inputs=('snapshot',))


def summary_snapshot(request, invocation):
    from stratbox.domains.minfin.analytics.snapshots import summary_snapshot as build
    return _tracked(request, invocation, lambda: build(request['summary'], dataset_id=request["dataset_id"], version_id=request["version_id"]), inputs=('summary',))


def read_summary(request, invocation):
    from stratbox.domains.minfin.analytics.snapshots import summary_from_snapshot as build
    return _tracked(request, invocation, lambda: build(request['snapshot']), inputs=('snapshot',))


def view_snapshot(request, invocation):
    from stratbox.shared.data.views import view_snapshot as build
    return _tracked(request, invocation, lambda: build(request['view'], dataset_id=request["dataset_id"], version_id=request["version_id"]), inputs=('view',))


def read_view(request, invocation):
    from stratbox.shared.data.views import view_from_snapshot as build
    return _tracked(request, invocation, lambda: build(request['snapshot']), inputs=('snapshot',))


def render_view(request, invocation):
    from stratbox.shared.data.views import render_observation_view as build
    return _tracked(request, invocation, lambda: build(request['view'], format=request["format"]), inputs=('view',))


def document_snapshot(request, invocation):
    from stratbox.domains.minfin.documents.snapshots import snapshot_document as build
    return _tracked(request, invocation, lambda: build(request['document'], dataset_id=request["dataset_id"], version_id=request["version_id"]), inputs=('document',))


def read_document(request, invocation):
    from stratbox.domains.minfin.documents.snapshots import document_from_dataset as build
    return _tracked(request, invocation, lambda: build(request['snapshot']), inputs=('snapshot',))


def render_document(request, invocation):
    from stratbox.shared.data.documents import readable_document as build
    return _tracked(request, invocation, lambda: build(request['document'].document), inputs=('document',))
