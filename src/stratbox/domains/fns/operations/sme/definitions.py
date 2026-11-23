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


DISCOVER = _registry_definition('fns.sme.discover', 1)

ACQUIRE = _registry_definition('fns.sme.acquire', 1)

PARSE = _registry_definition('fns.sme.parse', 1)

CAPTURE = _registry_definition('fns.sme.capture', 1)

READ = _registry_definition('fns.sme.read_representation', 1)

COMPARE = _registry_definition('fns.sme.compare', 2)


from ...tables.contracts import JsonFlake


EXTRACT = _registry_definition('fns.sme.extract', 1)
READABLE = _registry_definition('fns.sme.readable', 1)
VALIDATE = _registry_definition('fns.sme.validate', 1)
COMPARE_FLAKES = _registry_definition('fns.sme.compare_flakes', 1)
PROJECT = _registry_definition('fns.sme.project', 1)
ALIGN = _registry_definition('fns.sme.align', 1)
COMPARE_DATASETS = _registry_definition('fns.sme.compare_datasets', 1)
CALCULATE_CHANGES = _registry_definition('fns.sme.calculate_changes', 1)
CALCULATE_SHARES = _registry_definition('fns.sme.calculate_shares', 1)
VIEW = _registry_definition('fns.sme.view', 1)
RENDER = _registry_definition('fns.sme.render', 1)
RENDER_ARTIFACT = _registry_definition('fns.sme.render_artifact', 1)
READABLE_ARTIFACT = _registry_definition('fns.sme.readable_artifact', 1)
FLAKE_SNAPSHOT = _registry_definition('fns.sme.flake_snapshot', 1)
READ_FLAKE_SNAPSHOT = _registry_definition('fns.sme.read_flake_snapshot', 1)
PROJECTION_SNAPSHOT = _registry_definition('fns.sme.projection_snapshot', 1)
READ_PROJECTION_SNAPSHOT = _registry_definition('fns.sme.read_projection_snapshot', 1)
DATASET_SNAPSHOT = _registry_definition('fns.sme.dataset_snapshot', 1)
READ_DATASET_SNAPSHOT = _registry_definition('fns.sme.read_dataset_snapshot', 1)
CALCULATION_SNAPSHOT = _registry_definition('fns.sme.calculation_snapshot', 1)
READ_CALCULATION_SNAPSHOT = _registry_definition('fns.sme.read_calculation_snapshot', 1)
VIEW_SNAPSHOT = _registry_definition('fns.sme.view_snapshot', 1)
READ_VIEW_SNAPSHOT = _registry_definition('fns.sme.read_view_snapshot', 1)
PROCESS = _registry_definition('fns.sme.process', 1)
CAPTURE_FULL = _registry_definition('fns.sme.capture_full', 1)
