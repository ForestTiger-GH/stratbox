"""Minfin publisher data: four registries and one semantic operation owner.

Operation handlers are lazy; public import and registry inspection do not load
spreadsheet decoders or instantiate a second execution system.
"""
from __future__ import annotations

from .publications.catalog import families, family, all_sources
from .publications.contracts import (
    DiscoverRequest, AcquireRequest, InspectRequest, ReadableRequest,
    SourceCheckpoint, UpdateRequest, UpdateDecision, UpdatePlan,
    Asset, PublicationIndex, SourceSeries, SourceProfileRefs,
    PublicationMarker, MaterialVersion, ProcessingVersion,
)
from .publications.updates import checkpoint_for
from .tables.contracts import (
    ExtractRequest, CompareRequest, MapRequest, MetricBinding, RenderRequest,
    ValidateRequest, SerializeRequest, ReadRepresentationRequest,
    BuildFlakeRequest, FlakeTable, RenderFlakeRequest, TableExtract,
    SerializeFlakeRequest, ReadFlakeRequest, FlakeSnapshotRequest, ReadFlakeSnapshotRequest,
)
from .analytics.contracts import (
    SummaryRequest, HeadlineSummary, NoticeRequest, NoticePreparation,
)
from .operations.contracts import CaptureRequest
from .publications.context import PublicationContext, context_for
from .integration.contracts import RowBinding, IntegrateRequest, ObservationSnapshotRequest, ReadObservationsRequest
from .analytics.contracts import SummarySnapshotRequest, ReadSummaryRequest
from .documents.contracts import ExtractDocumentRequest, PublisherDocument, DocumentSnapshotRequest, ReadDocumentRequest, RenderDocumentRequest

_OPERATIONS = frozenset({
    "discover", "inspect", "acquire", "capture", "extract", "validate", "compare",
    "map_observations", "render_csv_cells", "readable_document",
    "serialize_extract", "read_representation", "plan_updates",
    "build_source_flake", "render_source_flake", "calculate_headlines",
    "prepare_notice_facts", "serialize_source_flake", "read_source_flake",
    "build_flake_snapshot", "read_flake_snapshot",
})


_PIPELINE = frozenset({"integrate", "build_observation_snapshot", "read_observations",
    "build_summary_snapshot", "read_summary", "prepare_view", "build_view_snapshot", "read_view", "render_view"})


_DOCUMENT_OPS = frozenset({"extract_document", "build_document_snapshot", "read_document", "render_document"})


def __getattr__(name):
    if name in _DOCUMENT_OPS:
        from importlib import import_module
        return getattr(import_module(".operations.document_handlers", __name__), name)
    if name in _PIPELINE:
        from importlib import import_module
        return getattr(import_module(".operations.pipeline_handlers", __name__), name)
    if name in {"PrepareHeadlineViewRequest", "ViewSnapshotRequest", "ReadViewRequest", "RenderViewRequest"}:
        from importlib import import_module
        return getattr(import_module(".products.contracts", __name__), name)
    if name in {"bind_family", "bind_series", "validate_all_profiles"}:
        from .operations import bindings
        return getattr(bindings, name)
    if name in _OPERATIONS:
        from importlib import import_module
        return getattr(import_module(".operations.handlers", __name__), name)
    raise AttributeError(name)


__all__ = (
    "families", "family", "all_sources", "DiscoverRequest", "AcquireRequest",
    "ExtractRequest", "CompareRequest", "MapRequest", "MetricBinding", "RenderRequest",
    "ValidateRequest", "InspectRequest", "ReadableRequest", "CaptureRequest",
    "SerializeRequest", "ReadRepresentationRequest", "SerializeFlakeRequest", "ReadFlakeRequest",
    "SourceCheckpoint", "UpdateRequest", "UpdateDecision", "UpdatePlan",
    "BuildFlakeRequest", "FlakeTable", "RenderFlakeRequest", "FlakeSnapshotRequest", "ReadFlakeSnapshotRequest",
    "SummaryRequest", "HeadlineSummary", "NoticeRequest", "NoticePreparation",
    "Asset", "PublicationIndex", "TableExtract", "checkpoint_for", *_OPERATIONS, *_PIPELINE,
    "PublicationContext", "context_for", "RowBinding", "IntegrateRequest", "ObservationSnapshotRequest",
    "ReadObservationsRequest", "SummarySnapshotRequest", "ReadSummaryRequest",
    "PrepareHeadlineViewRequest", "ViewSnapshotRequest", "ReadViewRequest", "RenderViewRequest",
    "ExtractDocumentRequest", "PublisherDocument", "DocumentSnapshotRequest", "ReadDocumentRequest", "RenderDocumentRequest", *_DOCUMENT_OPS,
)
