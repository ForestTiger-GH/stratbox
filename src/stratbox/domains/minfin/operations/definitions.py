"""Lightweight typed operation contracts for the Minfin domain."""
from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from ..publications.contracts import (
    AcquireRequest, AcquiredAsset, DiscoverRequest, InspectRequest, Inspection,
    PublicationIndex, ReadableDocument, ReadableRequest, UpdateRequest, UpdatePlan,
)
from ..tables.contracts import (
    CompareRequest, ExtractRequest, MapRequest, MappedObservations, RenderRequest,
    TableComparison, TableExtract, ValidateRequest, Validation, SerializeRequest,
    ReadRepresentationRequest, BuildFlakeRequest, FlakeTable, RenderFlakeRequest,
    SerializeFlakeRequest, ReadFlakeRequest, FlakeSnapshotRequest, ReadFlakeSnapshotRequest,
)
from ..analytics.contracts import SummaryRequest, HeadlineSummary, NoticeRequest, NoticePreparation
from .contracts import CaptureRequest, CaptureResult


DISCOVER = _registry_definition('minfin.discover')
INSPECT = _registry_definition('minfin.inspect')
ACQUIRE = _registry_definition('minfin.acquire')
EXTRACT = _registry_definition('minfin.extract')
CAPTURE = _registry_definition('minfin.capture')
VALIDATE = _registry_definition('minfin.validate')
COMPARE = _registry_definition('minfin.compare')
MAP = _registry_definition('minfin.map_observations')
RENDER = _registry_definition('minfin.render_csv')
READABLE = _registry_definition('minfin.readable')

SERIALIZE = _registry_definition('minfin.serialize')
READ_EXTRACT = _registry_definition('minfin.read_representation')


# Independently callable update, flake, headline and notice stages.

PLAN_UPDATES = _registry_definition('minfin.plan_updates')
BUILD_FLAKE = _registry_definition('minfin.build_flake')
RENDER_FLAKE = _registry_definition('minfin.render_flake')
SERIALIZE_FLAKE = _registry_definition('minfin.serialize_flake')
READ_FLAKE = _registry_definition('minfin.read_flake')
SUMMARIZE = _registry_definition('minfin.summarize')
PREPARE_NOTICE = _registry_definition('minfin.prepare_notice')


FLAKE_SNAPSHOT = _registry_definition('minfin.flake_snapshot')
READ_FLAKE_SNAPSHOT = _registry_definition('minfin.read_flake_snapshot')
