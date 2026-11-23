"""Independent physical, semantic, integrated, analytical and product operations."""

from stratbox.operations.declarations import definition as _registry_definition
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


EXTRACT = _registry_definition('frg.extract')
EXTRACT_SNAPSHOT = _registry_definition('frg.extract_snapshot')
READ_EXTRACT = _registry_definition('frg.read_extract')
VALIDATE = _registry_definition('frg.validate')
COMPARE = _registry_definition('frg.compare')
READABLE = _registry_definition('frg.readable')
BUILD_FLAKE = _registry_definition('frg.build_flake')
FLAKE_SNAPSHOT = _registry_definition('frg.flake_snapshot')
READ_FLAKE = _registry_definition('frg.read_flake')
INTEGRATE = _registry_definition('frg.integrate')
ALIGN = _registry_definition('frg.align')
HISTORY = _registry_definition('frg.build_history')
OBSERVATION_SNAPSHOT = _registry_definition('frg.observation_snapshot')
READ_OBSERVATIONS = _registry_definition('frg.read_observations')
CALCULATE = _registry_definition('frg.calculate')
PREPARE_VIEW = _registry_definition('frg.prepare_view')
VIEW_SNAPSHOT = _registry_definition('frg.view_snapshot')
READ_VIEW = _registry_definition('frg.read_view')
RENDER_VIEW = _registry_definition('frg.render_view')
