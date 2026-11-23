"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition

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


DISCOVER = _registry_definition('fns.1yur.discover')

ACQUIRE = _registry_definition('fns.1yur.acquire')

_RAR = frozenset({"archive_decoder"})

PARSE = _registry_definition('fns.1yur.parse')

CAPTURE = _registry_definition('fns.1yur.capture')

READ = _registry_definition('fns.1yur.read_representation')

COMPARE = _registry_definition('fns.1yur.compare')


from ...tables.legal_entities.extraction import WorkbookBundle


EXTRACT = _registry_definition('fns.1yur.extract')
READABLE = _registry_definition('fns.1yur.readable')
VALIDATE = _registry_definition('fns.1yur.validate')
COMPARE_FLAKES = _registry_definition('fns.1yur.compare_flakes')
PROJECT = _registry_definition('fns.1yur.project')
ALIGN = _registry_definition('fns.1yur.align')
COMPARE_DATASETS = _registry_definition('fns.1yur.compare_datasets')
CALCULATE_CHANGES = _registry_definition('fns.1yur.calculate_changes')
CALCULATE_SHARES = _registry_definition('fns.1yur.calculate_shares')
VIEW = _registry_definition('fns.1yur.view')
RENDER = _registry_definition('fns.1yur.render')
RENDER_ARTIFACT = _registry_definition('fns.1yur.render_artifact')
READABLE_ARTIFACT = _registry_definition('fns.1yur.readable_artifact')
FLAKE_SNAPSHOT = _registry_definition('fns.1yur.flake_snapshot')
READ_FLAKE_SNAPSHOT = _registry_definition('fns.1yur.read_flake_snapshot')
PROJECTION_SNAPSHOT = _registry_definition('fns.1yur.projection_snapshot')
READ_PROJECTION_SNAPSHOT = _registry_definition('fns.1yur.read_projection_snapshot')
DATASET_SNAPSHOT = _registry_definition('fns.1yur.dataset_snapshot')
READ_DATASET_SNAPSHOT = _registry_definition('fns.1yur.read_dataset_snapshot')
CALCULATION_SNAPSHOT = _registry_definition('fns.1yur.calculation_snapshot')
READ_CALCULATION_SNAPSHOT = _registry_definition('fns.1yur.read_calculation_snapshot')
VIEW_SNAPSHOT = _registry_definition('fns.1yur.view_snapshot')
READ_VIEW_SNAPSHOT = _registry_definition('fns.1yur.read_view_snapshot')
PROCESS = _registry_definition('fns.1yur.process')
CAPTURE_FULL = _registry_definition('fns.1yur.capture_full')
