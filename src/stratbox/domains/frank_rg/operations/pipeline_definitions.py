"""Independent physical, semantic, integrated, analytical and product operations."""
from stratbox.core.execution import InputPort, OperationDefinition, OperationSemantics, OutputPort, ProcessingStage as S
from stratbox.core.execution.semantics import ProcessingFunction
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

_REPORT = DataContract("frg.report", 1, DataRole.ORIGINALS)
_FLAKE = DataContract("frg.semantic_flake", 1, DataRole.EXTRACTS)
_FLAKE_SNAPSHOT = DataContract("frg.flake.snapshot", 1, DataRole.EXTRACTS)
_BATCH = DataContract("observations.batch", 1, DataRole.INTEGRATED)
_BATCH_SNAPSHOT = DataContract("observations.batch.snapshot", 1)
_GENERIC = DataContract("dataset.snapshot", 1)


def _op(name, request, response, stage, inputs, target, description, *, parameters=(), snapshot=False):
    outputs = (OutputPort("value", target),)
    if snapshot:
        outputs += (OutputPort("snapshot", _GENERIC),)
    return OperationDefinition("frg." + name, 1, "frg." + name + ".v1", request, response,
        processing=OperationSemantics(() if snapshot or name.startswith("read_") else (stage,),
            function=ProcessingFunction.ENCODE if snapshot else ProcessingFunction.REPLAY if name.startswith("read_") else ProcessingFunction.PROCESS, inputs=inputs, outputs=outputs,
            parameters=parameters, summary=description))


def _input(contract, path):
    return (InputPort(path, contract, path),)

EXTRACT = _op("extract", ExtractRequest, WorkbookExtract, S.EXTRACT, _input(_REPORT, "report"), WORKBOOK_EXTRACT,
    "Admit and extract physical workbook evidence with exact source, issue and asset identity.")
EXTRACT_SNAPSHOT = _op("extract_snapshot", ExtractSnapshotRequest, DatasetSnapshot, S.PRESERVE,
    _input(WORKBOOK_EXTRACT, "extract"), WORKBOOK_SNAPSHOT, "Encode all physical workbook evidence for neutral storage.",
    parameters=("dataset_id", "version_id"), snapshot=True)
READ_EXTRACT = _op("read_extract", ReadExtractRequest, WorkbookExtract, S.READ_EXTRACT,
    _input(WORKBOOK_SNAPSHOT, "snapshot"), WORKBOOK_EXTRACT, "Replay a complete retained physical workbook extract.")
VALIDATE = _op("validate", ValidateExtractRequest, ExtractValidation, S.VALIDATE,
    _input(WORKBOOK_EXTRACT, "extract"), DataContract("frg.extract.validation"), "Validate source binding, cell structure and formula-cache availability.")
COMPARE = _op("compare", CompareExtractRequest, WorkbookComparison, S.COMPARE,
    (InputPort("before", WORKBOOK_EXTRACT, "before"), InputPort("after", WORKBOOK_EXTRACT, "after")),
    DataContract("workbook.comparison"), "Compare physical cell evidence without assigning economic meaning.")
READABLE = _op("readable", ReadableRequest, Representation, S.READABLE, _input(WORKBOOK_EXTRACT, "extract"),
    DataContract("workbook.readable.jsonl", 1, DataRole.READABLE), "Render every extracted sheet and cell as source-faithful readable JSONL.")
BUILD_FLAKE = _op("build_flake", BuildFlakeRequest, SemanticFlake, S.EXTRACT,
    (InputPort("extract", WORKBOOK_EXTRACT, "extract"), InputPort("profile", DataContract("frg.semantic_profile"), "profile")), _FLAKE,
    "Interpret explicitly bound cells using a typed byte-bound profile with units, periods, subjects and perimeters.")
FLAKE_SNAPSHOT = _op("flake_snapshot", FlakeSnapshotRequest, DatasetSnapshot, S.PRESERVE, _input(_FLAKE, "flake"),
    _FLAKE_SNAPSHOT, "Retain the semantic flake with source identity, profile identity and complete qualified observations.",
    parameters=("dataset_id", "version_id"), snapshot=True)
READ_FLAKE = _op("read_flake", ReadFlakeRequest, SemanticFlake, S.READ_EXTRACT, _input(_FLAKE_SNAPSHOT, "snapshot"),
    _FLAKE, "Replay a semantic flake independently of workbook readers and current profiles.")
INTEGRATE = _op("integrate", IntegrateRequest, ObservationBatch, S.INTEGRATE, _input(_FLAKE, "flake"), _BATCH,
    "Place admitted source-local observations in an explicitly named integrated dataset.", parameters=("dataset_id", "release_id"))
ALIGN = _op("align", AlignRequest, ObservationBatch, S.INTEGRATE,
    _input(DataContract("observations.batch.collection"), "batches"), _BATCH,
    "Align explicitly supplied batches with exact metric contracts; ambiguous duplicates are rejected.", parameters=("dataset_id", "release_id"))
HISTORY = _op("build_history", HistoryRequest, ObservationBatch, S.INTEGRATE,
    _input(DataContract("observations.batch.collection"), "batches"), _BATCH,
    "Preserve every supplied publication release in explicit history dimensions without selecting an implicit latest vintage.",
    parameters=("dataset_id", "release_id"))
OBSERVATION_SNAPSHOT = _op("observation_snapshot", ObservationSnapshotRequest, DatasetSnapshot, S.INGEST,
    _input(_BATCH, "batch"), _BATCH_SNAPSHOT, "Encode integrated, historical or calculated observations for the selected logical store.",
    parameters=("dataset_id", "version_id"), snapshot=True)
READ_OBSERVATIONS = _op("read_observations", ReadObservationsRequest, ObservationBatch, S.READ_EXTRACT,
    _input(_BATCH_SNAPSHOT, "snapshot"), _BATCH, "Restore complete qualified observations with all source and profile lineage.")
CALCULATE = _op("calculate", CalculateRequest, ObservationBatch, S.CALCULATE,
    (InputPort("before", _BATCH, "before"), InputPort("after", _BATCH, "after")), _BATCH,
    "Calculate exact same-period revision deltas; missing, added, removed or incompatible values remain explicitly qualified.",
    parameters=("dataset_id", "release_id"))
PREPARE_VIEW = _op("prepare_view", PrepareViewRequest, ObservationView, S.VIEW, _input(_BATCH, "batch"), OBSERVATION_VIEW,
    "Prepare an explicit selection of qualified observations without aggregation or source reopening.",
    parameters=("view_id", "metric_ids", "period_kinds", "subject_ids"))
VIEW_SNAPSHOT = _op("view_snapshot", ViewSnapshotRequest, DatasetSnapshot, S.PRESERVE,
    _input(OBSERVATION_VIEW, "view"), OBSERVATION_VIEW_SNAPSHOT, "Persist every prepared view value, coverage statement and evidence reference.",
    parameters=("dataset_id", "version_id"), snapshot=True)
READ_VIEW = _op("read_view", ReadViewRequest, ObservationView, S.READ_EXTRACT, _input(OBSERVATION_VIEW_SNAPSHOT, "snapshot"),
    OBSERVATION_VIEW, "Restore a prepared observation view independently of analytics and source readers.")
RENDER_VIEW = _op("render_view", RenderViewRequest, Representation, S.RENDER, _input(OBSERVATION_VIEW, "view"),
    DataContract("observations.view.representation", 1, DataRole.PRODUCTS), "Render the prepared qualified view as CSV, JSON or JSONL.", parameters=("format",))
