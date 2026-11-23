"""Portable metadata for reusable processing stages; optional engines stay lazy."""

from stratbox.core.registry.operations import definition as _registry_definition
from dataclasses import dataclass

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.workbooks import WorkbookExtract, WorkbookComparison, WORKBOOK_EXTRACT, WORKBOOK_SNAPSHOT as WORKBOOK_SNAPSHOT_CONTRACT
from stratbox.shared.data.documents import DocumentExtract, DOCUMENT_EXTRACT, DOCUMENT_SNAPSHOT as DOCUMENT_SNAPSHOT_CONTRACT
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.views import ObservationView, OBSERVATION_VIEW, OBSERVATION_VIEW_SNAPSHOT
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.updates import ProcessingTarget, RetainedProcessing, UpdatePlan

LIMITS = ExecutionBudget(input_bytes=512*1024*1024, output_bytes=512*1024*1024, cells=80_000_000)
SNAPSHOT = DataContract("dataset.snapshot")
PAYLOAD = DataContract("source.payload", role=DataRole.ORIGINALS)
BATCH = DataContract("observations.batch", role=DataRole.INTEGRATED)


@dataclass(frozen=True, slots=True)
class ExtractRequest:
    payload: SourcePayload
    series_id: str
    issue_id: str
    asset_id: str = "main"


@dataclass(frozen=True, slots=True)
class WorkbookRequest:
    workbook: WorkbookExtract


@dataclass(frozen=True, slots=True)
class DocumentRequest:
    document: DocumentExtract


@dataclass(frozen=True, slots=True)
class SnapshotRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True, slots=True)
class CompareWorkbooksRequest:
    before: WorkbookExtract
    after: WorkbookExtract


@dataclass(frozen=True, slots=True)
class PrepareViewRequest:
    batch: ObservationBatch
    view_id: str
    metric_ids: tuple[str, ...] = ()
    period_kinds: tuple[str, ...] = ()
    subject_ids: tuple[str, ...] = ()
    coverage: SnapshotCoverage | None = None
    qualifications: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewRequest:
    view: ObservationView
    format: str = "csv"


@dataclass(frozen=True, slots=True)
class UpdatePlanRequest:
    targets: tuple[ProcessingTarget, ...]
    retained: tuple[RetainedProcessing, ...] = ()
    coverage: SnapshotCoverage | None = None


WORKBOOK = _registry_definition('workbook.extract')
WORKBOOK_READABLE = _registry_definition('workbook.readable')
WORKBOOK_SNAPSHOT = _registry_definition('workbook.snapshot')
WORKBOOK_REPLAY = _registry_definition('workbook.replay')
WORKBOOK_COMPARE = _registry_definition('workbook.compare')
DOCUMENT = _registry_definition('document.extract')
DOCUMENT_READABLE = _registry_definition('document.readable')
DOCUMENT_SNAPSHOT = _registry_definition('document.snapshot')
DOCUMENT_REPLAY = _registry_definition('document.replay')
VIEW = _registry_definition('observations.prepare_view')
VIEW_SNAPSHOT = _registry_definition('observations.view_snapshot')
VIEW_REPLAY = _registry_definition('observations.replay_view')
VIEW_RENDER = _registry_definition('observations.render_view')

UPDATE = _registry_definition('processing.plan_update')
