"""Minfin publisher families and independent, source-faithful operations.

Descriptions live in root REGISTRY_*.yaml resources. The domain's operation
implementation remains lazy during global registration/discovery.
"""
from .registry import families, family, all_sources
from .models import (
    DiscoverRequest, AcquireRequest, ExtractRequest, CompareRequest, MapRequest,
    MetricBinding, RenderRequest, ValidateRequest, InspectRequest, ReadableRequest,
    SerializeRequest, ReadRepresentationRequest, CaptureRequest,
)

_OPERATIONS = frozenset({
    'discover', 'inspect', 'acquire', 'capture', 'extract', 'validate', 'compare',
    'map_observations', 'render_csv_cells', 'readable_document',
    'serialize_extract', 'read_representation',
})


def __getattr__(name):
    if name in _OPERATIONS:
        from importlib import import_module
        return getattr(import_module('.operations', __name__), name)
    raise AttributeError(name)


__all__ = (
    'families', 'family', 'all_sources', 'DiscoverRequest', 'AcquireRequest',
    'ExtractRequest', 'CompareRequest', 'MapRequest', 'MetricBinding', 'RenderRequest',
    'ValidateRequest', 'InspectRequest', 'ReadableRequest', 'CaptureRequest',
    'SerializeRequest', 'ReadRepresentationRequest', *_OPERATIONS,
)