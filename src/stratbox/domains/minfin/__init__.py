"""Minfin publisher data: four registries and one semantic operation owner.

Operation handlers are lazy; public import and registry inspection do not load
spreadsheet decoders or instantiate a second execution system.
"""
from __future__ import annotations

from .publications.catalog import families, family, all_sources
from .publications.contracts import (
    DiscoverRequest, AcquireRequest, InspectRequest, ReadableRequest,
    SourceCheckpoint, UpdateRequest, UpdateDecision, UpdatePlan,
    Asset, PublicationIndex,
)
from .publications.updates import checkpoint_for
from .tables.contracts import (
    ExtractRequest, CompareRequest, MapRequest, MetricBinding, RenderRequest,
    ValidateRequest, SerializeRequest, ReadRepresentationRequest,
    BuildFlakeRequest, FlakeTable, RenderFlakeRequest, TableExtract,
)
from .analytics.contracts import (
    SummaryRequest, HeadlineSummary, NoticeRequest, NoticePreparation,
)
from .operations.contracts import CaptureRequest

_OPERATIONS = frozenset({
    "discover", "inspect", "acquire", "capture", "extract", "validate", "compare",
    "map_observations", "render_csv_cells", "readable_document",
    "serialize_extract", "read_representation", "plan_updates",
    "build_source_flake", "render_source_flake", "calculate_headlines",
    "prepare_notice_facts",
})


def __getattr__(name):
    if name in _OPERATIONS:
        from importlib import import_module
        return getattr(import_module(".operations.handlers", __name__), name)
    raise AttributeError(name)


__all__ = (
    "families", "family", "all_sources", "DiscoverRequest", "AcquireRequest",
    "ExtractRequest", "CompareRequest", "MapRequest", "MetricBinding", "RenderRequest",
    "ValidateRequest", "InspectRequest", "ReadableRequest", "CaptureRequest",
    "SerializeRequest", "ReadRepresentationRequest",
    "SourceCheckpoint", "UpdateRequest", "UpdateDecision", "UpdatePlan",
    "BuildFlakeRequest", "FlakeTable", "RenderFlakeRequest",
    "SummaryRequest", "HeadlineSummary", "NoticeRequest", "NoticePreparation",
    "Asset", "PublicationIndex", "TableExtract", "checkpoint_for", *_OPERATIONS,
)
