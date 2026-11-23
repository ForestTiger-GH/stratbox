"""Independent integration, durable calculation and product boundaries."""

from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.views import ObservationView, OBSERVATION_VIEW, OBSERVATION_VIEW_SNAPSHOT
from ..integration.contracts import IntegrateRequest, ObservationSnapshotRequest, ReadObservationsRequest
from ..analytics.contracts import HeadlineSummary, SummarySnapshotRequest, ReadSummaryRequest
from ..products.contracts import PrepareHeadlineViewRequest, ViewSnapshotRequest, ReadViewRequest, RenderViewRequest


INTEGRATE = _registry_definition('minfin.integrate')
OBSERVATION_SNAPSHOT = _registry_definition('minfin.observation_snapshot')
READ_OBSERVATIONS = _registry_definition('minfin.read_observations')
SUMMARY_SNAPSHOT = _registry_definition('minfin.summary_snapshot')
READ_SUMMARY = _registry_definition('minfin.read_summary')
PREPARE_VIEW = _registry_definition('minfin.prepare_view')
VIEW_SNAPSHOT = _registry_definition('minfin.view_snapshot')
READ_VIEW = _registry_definition('minfin.read_view')
RENDER_VIEW = _registry_definition('minfin.render_view')
