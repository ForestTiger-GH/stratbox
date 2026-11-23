"""Lightweight typed operation contracts for the Minfin domain."""
from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

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


DISCOVER = _registry_definition('minfin.discover', 1)
INSPECT = _registry_definition('minfin.inspect', 1)
ACQUIRE = _registry_definition('minfin.acquire', 1)
EXTRACT = _registry_definition('minfin.extract', 1)
CAPTURE = _registry_definition('minfin.capture', 1)
VALIDATE = _registry_definition('minfin.validate', 1)
COMPARE = _registry_definition('minfin.compare', 1)
MAP = _registry_definition('minfin.map_observations', 1)
RENDER = _registry_definition('minfin.render_csv', 1)
READABLE = _registry_definition('minfin.readable', 1)

SERIALIZE = _registry_definition('minfin.serialize', 1)
READ_EXTRACT = _registry_definition('minfin.read_representation', 1)


# Independently callable update, flake, headline and notice stages.

PLAN_UPDATES = _registry_definition('minfin.plan_updates', 1)
BUILD_FLAKE = _registry_definition('minfin.build_flake', 1)
RENDER_FLAKE = _registry_definition('minfin.render_flake', 1)
SERIALIZE_FLAKE = _registry_definition('minfin.serialize_flake', 1)
READ_FLAKE = _registry_definition('minfin.read_flake', 1)
SUMMARIZE = _registry_definition('minfin.summarize', 1)
PREPARE_NOTICE = _registry_definition('minfin.prepare_notice', 1)


FLAKE_SNAPSHOT = _registry_definition('minfin.flake_snapshot', 1)
READ_FLAKE_SNAPSHOT = _registry_definition('minfin.read_flake_snapshot', 1)
