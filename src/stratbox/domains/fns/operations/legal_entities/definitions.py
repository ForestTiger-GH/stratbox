"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from dataclasses import dataclass
from datetime import date
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
    ReleaseLink,
)

from stratbox.shared.data.processing import DataContract, DataRole

DATASET = "fns.1yur"

METHOD = "fns-1yur-part-i-1"

_HTTP = frozenset({"http"})


@dataclass(frozen=True, slots=True)
class Discover1YurRequest:
    year: int
    index: SourcePayload | None = None
    index_url: str | None = None


@dataclass(frozen=True, slots=True)
class ReleaseIndex:
    releases: tuple[ReleaseLink, ...]
    missing_assets: tuple[date, ...]


@dataclass(frozen=True, slots=True)
class Parse1YurRequest:
    payload: SourcePayload
    as_of: date


DISCOVER = _registry_definition('fns.1yur.discover', 1)

ACQUIRE = _registry_definition('fns.1yur.acquire', 1)

_RAR = frozenset({"archive_decoder"})

PARSE = _registry_definition('fns.1yur.parse', 1)

CAPTURE = _registry_definition('fns.1yur.capture', 1)

READ = _registry_definition('fns.1yur.read_representation', 1)

COMPARE = _registry_definition('fns.1yur.compare', 2)


from ...tables.legal_entities.extraction import WorkbookBundle


EXTRACT = _registry_definition('fns.1yur.extract', 1)
READABLE = _registry_definition('fns.1yur.readable', 1)
VALIDATE = _registry_definition('fns.1yur.validate', 1)
COMPARE_FLAKES = _registry_definition('fns.1yur.compare_flakes', 1)
PROJECT = _registry_definition('fns.1yur.project', 1)
ALIGN = _registry_definition('fns.1yur.align', 1)
COMPARE_DATASETS = _registry_definition('fns.1yur.compare_datasets', 1)
CALCULATE_CHANGES = _registry_definition('fns.1yur.calculate_changes', 1)
CALCULATE_SHARES = _registry_definition('fns.1yur.calculate_shares', 1)
VIEW = _registry_definition('fns.1yur.view', 1)
RENDER = _registry_definition('fns.1yur.render', 1)
RENDER_ARTIFACT = _registry_definition('fns.1yur.render_artifact', 1)
READABLE_ARTIFACT = _registry_definition('fns.1yur.readable_artifact', 1)
FLAKE_SNAPSHOT = _registry_definition('fns.1yur.flake_snapshot', 1)
READ_FLAKE_SNAPSHOT = _registry_definition('fns.1yur.read_flake_snapshot', 1)
PROJECTION_SNAPSHOT = _registry_definition('fns.1yur.projection_snapshot', 1)
READ_PROJECTION_SNAPSHOT = _registry_definition('fns.1yur.read_projection_snapshot', 1)
DATASET_SNAPSHOT = _registry_definition('fns.1yur.dataset_snapshot', 1)
READ_DATASET_SNAPSHOT = _registry_definition('fns.1yur.read_dataset_snapshot', 1)
CALCULATION_SNAPSHOT = _registry_definition('fns.1yur.calculation_snapshot', 1)
READ_CALCULATION_SNAPSHOT = _registry_definition('fns.1yur.read_calculation_snapshot', 1)
VIEW_SNAPSHOT = _registry_definition('fns.1yur.view_snapshot', 1)
READ_VIEW_SNAPSHOT = _registry_definition('fns.1yur.read_view_snapshot', 1)
PROCESS = _registry_definition('fns.1yur.process', 1)
CAPTURE_FULL = _registry_definition('fns.1yur.capture_full', 1)
