"""Minfin publisher families and independent, source-faithful operations.

Descriptions live in root REGISTRY_*.yaml resources. The domain's operation
implementation remains lazy during global registration/discovery.
"""
from .registry import families, family, all_sources
from .pipeline_models import (
    SourceCheckpoint, UpdateRequest, UpdateDecision, UpdatePlan,
    BuildFlakeRequest, FlakeTable, RenderFlakeRequest,
    SummaryRequest, HeadlineSummary, NoticeRequest, NoticePreparation,
)
from .updates import checkpoint_for
from .models import (
    DiscoverRequest, AcquireRequest, ExtractRequest, CompareRequest, MapRequest,
    MetricBinding, RenderRequest, ValidateRequest, InspectRequest, ReadableRequest,
    SerializeRequest, ReadRepresentationRequest, CaptureRequest,
)

_OPERATIONS = frozenset({
    'discover', 'inspect', 'acquire', 'capture', 'extract', 'validate', 'compare',
    'map_observations', 'render_csv_cells', 'readable_document',
    'serialize_extract', 'read_representation',
    'plan_updates', 'build_source_flake', 'render_source_flake',
    'calculate_headlines', 'prepare_notice_facts',
})


def __getattr__(name):
    if name in _OPERATIONS:
        from importlib import import_module
        module = '.pipeline_operations' if name in {
            'plan_updates', 'build_source_flake', 'render_source_flake',
            'calculate_headlines', 'prepare_notice_facts',
        } else '.operations'
        return getattr(import_module(module, __name__), name)
    raise AttributeError(name)


__all__ = (
    'families', 'family', 'all_sources', 'DiscoverRequest', 'AcquireRequest',
    'ExtractRequest', 'CompareRequest', 'MapRequest', 'MetricBinding', 'RenderRequest',
    'ValidateRequest', 'InspectRequest', 'ReadableRequest', 'CaptureRequest',
    'SerializeRequest', 'ReadRepresentationRequest',
    'SourceCheckpoint', 'UpdateRequest', 'UpdateDecision', 'UpdatePlan',
    'BuildFlakeRequest', 'FlakeTable', 'RenderFlakeRequest',
    'SummaryRequest', 'HeadlineSummary', 'NoticeRequest', 'NoticePreparation',
    'checkpoint_for', *_OPERATIONS,
)