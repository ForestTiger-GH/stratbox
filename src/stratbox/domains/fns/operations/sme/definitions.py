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
)

from stratbox.shared.data.processing import DataContract, DataRole

DATASET = "fns.sme"

METHOD = "fns-sme-regional-json-1"

_HTTP = frozenset({"http"})


@dataclass(frozen=True, slots=True)
class DiscoverSmeRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class AcquireSmeRequest:
    as_of: date


@dataclass(frozen=True, slots=True)
class ParseSmeRequest:
    payload: SourcePayload
    as_of: date


DISCOVER = _registry_definition('fns.sme.discover')

ACQUIRE = _registry_definition('fns.sme.acquire')

PARSE = _registry_definition('fns.sme.parse')

CAPTURE = _registry_definition('fns.sme.capture')

READ = _registry_definition('fns.sme.read_representation')

COMPARE = _registry_definition('fns.sme.compare')


from ...tables.contracts import JsonFlake


EXTRACT = _registry_definition('fns.sme.extract')
READABLE = _registry_definition('fns.sme.readable')
VALIDATE = _registry_definition('fns.sme.validate')
COMPARE_FLAKES = _registry_definition('fns.sme.compare_flakes')
PROJECT = _registry_definition('fns.sme.project')
ALIGN = _registry_definition('fns.sme.align')
COMPARE_DATASETS = _registry_definition('fns.sme.compare_datasets')
CALCULATE_CHANGES = _registry_definition('fns.sme.calculate_changes')
CALCULATE_SHARES = _registry_definition('fns.sme.calculate_shares')
VIEW = _registry_definition('fns.sme.view')
RENDER = _registry_definition('fns.sme.render')
RENDER_ARTIFACT = _registry_definition('fns.sme.render_artifact')
READABLE_ARTIFACT = _registry_definition('fns.sme.readable_artifact')
FLAKE_SNAPSHOT = _registry_definition('fns.sme.flake_snapshot')
READ_FLAKE_SNAPSHOT = _registry_definition('fns.sme.read_flake_snapshot')
PROJECTION_SNAPSHOT = _registry_definition('fns.sme.projection_snapshot')
READ_PROJECTION_SNAPSHOT = _registry_definition('fns.sme.read_projection_snapshot')
DATASET_SNAPSHOT = _registry_definition('fns.sme.dataset_snapshot')
READ_DATASET_SNAPSHOT = _registry_definition('fns.sme.read_dataset_snapshot')
CALCULATION_SNAPSHOT = _registry_definition('fns.sme.calculation_snapshot')
READ_CALCULATION_SNAPSHOT = _registry_definition('fns.sme.read_calculation_snapshot')
VIEW_SNAPSHOT = _registry_definition('fns.sme.view_snapshot')
READ_VIEW_SNAPSHOT = _registry_definition('fns.sme.read_view_snapshot')
PROCESS = _registry_definition('fns.sme.process')
CAPTURE_FULL = _registry_definition('fns.sme.capture_full')
