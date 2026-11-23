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


INTEGRATE = _registry_definition('minfin.integrate', 1)
OBSERVATION_SNAPSHOT = _registry_definition('minfin.observation_snapshot', 1)
READ_OBSERVATIONS = _registry_definition('minfin.read_observations', 1)
SUMMARY_SNAPSHOT = _registry_definition('minfin.summary_snapshot', 1)
READ_SUMMARY = _registry_definition('minfin.read_summary', 1)
PREPARE_VIEW = _registry_definition('minfin.prepare_view', 1)
VIEW_SNAPSHOT = _registry_definition('minfin.view_snapshot', 1)
READ_VIEW = _registry_definition('minfin.read_view', 1)
RENDER_VIEW = _registry_definition('minfin.render_view', 1)
