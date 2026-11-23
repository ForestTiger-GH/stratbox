"""Portable metadata for reusable processing stages; optional engines stay lazy."""
from dataclasses import dataclass

from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage as S, ProcessingFunction as F
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.workbooks import WorkbookExtract, WorkbookComparison, WORKBOOK_EXTRACT
from stratbox.shared.data.documents import DocumentExtract, DOCUMENT_EXTRACT
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.views import ObservationView, OBSERVATION_VIEW
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.updates import ProcessingTarget, RetainedProcessing, UpdatePlan

LIMITS = ExecutionBudget(input_bytes=128*1024*1024, output_bytes=512*1024*1024, cells=5_000_000)
SNAPSHOT = DataContract("dataset.snapshot")
PAYLOAD = DataContract("material.source", role=DataRole.ORIGINALS)
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


def definition(op, request, value, stages, inputs, output, *, function=F.PROCESS, parameters=(), summary):
    return OperationDefinition(op, 1, op.replace(".", "-")+"-1", request, value, limits=LIMITS,
        processing=OperationSemantics(stages, inputs, (output,), parameters, summary, function=function))


WORKBOOK = definition("workbook.extract", ExtractRequest, WorkbookExtract, (S.EXTRACT,),
    (InputPort("source", PAYLOAD, "payload"),), OutputPort("workbook", WORKBOOK_EXTRACT),
    parameters=("series_id", "issue_id", "asset_id"), summary="Extract all decoder-visible workbook cells with exact format-specific evidence.")
WORKBOOK_READABLE = definition("workbook.readable", WorkbookRequest, Representation, (S.READABLE,),
    (InputPort("workbook", WORKBOOK_EXTRACT, "workbook"),), OutputPort("readable", DataContract("workbook.readable.jsonl", role=DataRole.READABLE)),
    summary="Render physical cell evidence as source-readable JSONL without assigning economic meaning.")
WORKBOOK_SNAPSHOT = definition("workbook.snapshot", WorkbookRequest, DatasetSnapshot, (),
    (InputPort("workbook", WORKBOOK_EXTRACT, "workbook"),), OutputPort("snapshot", SNAPSHOT), function=F.ENCODE,
    summary="Encode a complete workbook extract into independently addressable sheet partitions.")
WORKBOOK_REPLAY = definition("workbook.replay", SnapshotRequest, WorkbookExtract, (),
    (InputPort("snapshot", SNAPSHOT, "snapshot"),), OutputPort("workbook", WORKBOOK_EXTRACT), function=F.REPLAY,
    summary="Restore every physical cell and source context from a verified workbook snapshot.")
WORKBOOK_COMPARE = definition("workbook.compare", CompareWorkbooksRequest, WorkbookComparison, (S.COMPARE,),
    (InputPort("before", WORKBOOK_EXTRACT, "before"), InputPort("after", WORKBOOK_EXTRACT, "after")),
    OutputPort("comparison", DataContract("workbook.cell_comparison")), summary="Compare exact physical cells and geometry without assuming economic comparability.")
DOCUMENT = definition("document.extract", ExtractRequest, DocumentExtract, (S.EXTRACT,),
    (InputPort("source", PAYLOAD, "payload"),), OutputPort("document", DOCUMENT_EXTRACT),
    parameters=("series_id", "issue_id", "asset_id"), summary="Extract ordered text blocks and explicit document extraction qualifications.")
DOCUMENT_READABLE = definition("document.readable", DocumentRequest, Representation, (S.READABLE,),
    (InputPort("document", DOCUMENT_EXTRACT, "document"),), OutputPort("readable", DataContract("document.readable.jsonl", role=DataRole.READABLE)),
    summary="Render ordered document evidence and its source context as JSONL.")
DOCUMENT_SNAPSHOT = definition("document.snapshot", DocumentRequest, DatasetSnapshot, (),
    (InputPort("document", DOCUMENT_EXTRACT, "document"),), OutputPort("snapshot", SNAPSHOT), function=F.ENCODE,
    summary="Encode document blocks and qualifications for independent retention.")
DOCUMENT_REPLAY = definition("document.replay", SnapshotRequest, DocumentExtract, (),
    (InputPort("snapshot", SNAPSHOT, "snapshot"),), OutputPort("document", DOCUMENT_EXTRACT), function=F.REPLAY,
    summary="Restore ordered document evidence without reacquiring the original.")
VIEW = definition("observations.prepare_view", PrepareViewRequest, ObservationView, (S.VIEW,),
    (InputPort("batch", BATCH, "batch"),), OutputPort("view", OBSERVATION_VIEW),
    parameters=("view_id", "metric_ids", "period_kinds", "subject_ids", "coverage", "qualifications"),
    summary="Prepare an explicit observation selection preserving periods, missing states and provenance.")
VIEW_SNAPSHOT = definition("observations.view_snapshot", ViewRequest, DatasetSnapshot, (),
    (InputPort("view", OBSERVATION_VIEW, "view"),), OutputPort("snapshot", SNAPSHOT), function=F.ENCODE,
    summary="Encode a prepared observation view for independent replay.")
VIEW_REPLAY = definition("observations.replay_view", SnapshotRequest, ObservationView, (),
    (InputPort("snapshot", SNAPSHOT, "snapshot"),), OutputPort("view", OBSERVATION_VIEW), function=F.REPLAY,
    summary="Restore a verified prepared observation view with its original selection provenance.")
VIEW_RENDER = definition("observations.render_view", ViewRequest, Representation, (S.RENDER,),
    (InputPort("view", OBSERVATION_VIEW, "view"),), OutputPort("product", DataContract("observations.rendered_view", role=DataRole.PRODUCTS)),
    parameters=("format",), summary="Render a prepared observation view to exact long-form CSV, JSON or JSONL.")

UPDATE = definition("processing.plan_update", UpdatePlanRequest, UpdatePlan, (S.INSPECT,), (),
    OutputPort("plan", DataContract("processing.update_plan")), function=F.INSPECT,
    parameters=("targets", "retained", "coverage"),
    summary="Plan independent source, method, reference-edition and destination updates without performing effects.")
