"""Independent physical, semantic, integrated, analytical and product operations."""

from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.workbooks import WorkbookExtract, WorkbookComparison, WORKBOOK_EXTRACT, WORKBOOK_SNAPSHOT
from stratbox.shared.data.views import ObservationView, OBSERVATION_VIEW, OBSERVATION_VIEW_SNAPSHOT
from ..tables.contracts import (ExtractRequest, ExtractSnapshotRequest, ReadExtractRequest, ValidateExtractRequest,
    ExtractValidation, CompareExtractRequest, ReadableRequest, BuildFlakeRequest, SemanticFlake, FlakeSnapshotRequest, ReadFlakeRequest)
from ..integration.contracts import IntegrateRequest, AlignRequest, HistoryRequest, ObservationSnapshotRequest, ReadObservationsRequest
from ..analytics.contracts import CalculateRequest
from ..products.contracts import PrepareViewRequest, ViewSnapshotRequest, ReadViewRequest, RenderViewRequest


EXTRACT = _registry_definition('frg.extract', 1)
EXTRACT_SNAPSHOT = _registry_definition('frg.extract_snapshot', 1)
READ_EXTRACT = _registry_definition('frg.read_extract', 1)
VALIDATE = _registry_definition('frg.validate', 1)
COMPARE = _registry_definition('frg.compare', 1)
READABLE = _registry_definition('frg.readable', 1)
BUILD_FLAKE = _registry_definition('frg.build_flake', 1)
FLAKE_SNAPSHOT = _registry_definition('frg.flake_snapshot', 1)
READ_FLAKE = _registry_definition('frg.read_flake', 1)
INTEGRATE = _registry_definition('frg.integrate', 1)
ALIGN = _registry_definition('frg.align', 1)
HISTORY = _registry_definition('frg.build_history', 1)
OBSERVATION_SNAPSHOT = _registry_definition('frg.observation_snapshot', 1)
READ_OBSERVATIONS = _registry_definition('frg.read_observations', 1)
CALCULATE = _registry_definition('frg.calculate', 1)
PREPARE_VIEW = _registry_definition('frg.prepare_view', 1)
VIEW_SNAPSHOT = _registry_definition('frg.view_snapshot', 1)
READ_VIEW = _registry_definition('frg.read_view', 1)
RENDER_VIEW = _registry_definition('frg.render_view', 1)
