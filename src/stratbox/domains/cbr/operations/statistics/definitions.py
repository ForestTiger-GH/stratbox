"""Executable stage and port contracts for statistical workbooks and products."""
from stratbox.core.execution import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage as S
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake, WorkbookValidation, WorkbookComparison
from stratbox.domains.cbr.tables.statistics.snapshots import FLAKE
from stratbox.domains.cbr.integration.statistics.contracts import StatisticsDataset
from stratbox.domains.cbr.integration.statistics.snapshots import DATASET
from stratbox.domains.cbr.products.statistics.views import VIEW, StatisticsView
from . import contracts as C

_LIMITS = ExecutionBudget(input_bytes=256 * 1024**2, output_bytes=256 * 1024**2,
                          temporary_bytes=256 * 1024**2, cells=5_000_000)
_SNAPSHOT = DataContract("dataset.snapshot")


def _definition(name, stage, request, result, inputs, outputs, *, parameters=(), summary):
    return OperationDefinition(name, 1, name.replace(".", "-") + "-1", request, result, limits=_LIMITS,
        processing=OperationSemantics((stage,), inputs=inputs, outputs=outputs, parameters=parameters, summary=summary))


EXTRACT = _definition("cbr.tables.extract", S.EXTRACT, C.ExtractWorkbookRequest, WorkbookFlake,
    (InputPort("original", DataContract("cbr.publication.original", 1, DataRole.ORIGINALS), "original"),),
    (OutputPort("flake", FLAKE),),
    summary="Extract every physical cell, formula and source note before statistical or model selection.")
VALIDATE = _definition("cbr.tables.validate", S.VALIDATE, C.FlakeRequest, WorkbookValidation,
    (InputPort("flake", FLAKE, "flake"),), (OutputPort("validation", DataContract("cbr.workbook.validation")),),
    summary="Validate source editions, unknown sheets and missing formula caches with explicit diagnostics.")
COMPARE = _definition("cbr.tables.compare", S.COMPARE, C.CompareWorkbooksRequest, WorkbookComparison,
    (InputPort("before", FLAKE, "before"), InputPort("after", FLAKE, "after")),
    (OutputPort("comparison", DataContract("cbr.workbook.comparison")),),
    summary="Compare exact source releases independently of processing and destination state.")
READABLE = _definition("cbr.tables.readable", S.READABLE, C.FlakeRequest, Representation,
    (InputPort("flake", FLAKE, "flake"),),
    (OutputPort("readable", DataContract("cbr.workbook.readable", 1, DataRole.READABLE)),),
    summary="Render source-readable JSONL containing every cell without economic interpretation.")
FLAKE_SNAPSHOT = _definition("cbr.tables.flake_snapshot", S.EXTRACT, C.FlakeRequest, DatasetSnapshot,
    (InputPort("flake", FLAKE, "flake"),), (OutputPort("snapshot", _SNAPSHOT),),
    summary="Encode a complete flake as portable typed tables; this operation performs no persistence.")
READ_FLAKE_SNAPSHOT = _definition("cbr.tables.read_flake_snapshot", S.READ_EXTRACT, C.ReadSnapshotRequest, WorkbookFlake,
    (InputPort("snapshot", _SNAPSHOT, "snapshot"),), (OutputPort("flake", FLAKE),),
    summary="Restore and validate all source cells from a complete retained snapshot.")
ALIGN = _definition("cbr.statistics.align", S.INTEGRATE, C.AlignStatisticsRequest, StatisticsDataset,
    (InputPort("flakes", DataContract("cbr.workbook.flake_collection", 1, DataRole.EXTRACTS), "flakes"),),
    (OutputPort("dataset", DATASET),), parameters=("row_bindings", "period_bindings", "mapping_version", "strict"),
    summary="Align qualified source periods and units with explicit identities, mappings and unresolved semantics.")
CHANGE = _definition("cbr.statistics.calculate_change", S.CALCULATE, C.CalculateChangeRequest, StatisticsDataset,
    (InputPort("dataset", DATASET, "dataset"),), (OutputPort("dataset", DATASET),),
    parameters=("before", "after", "method", "release_ids"),
    summary="Calculate a selected absolute or percentage change separately from published adjusted growth.")
SHARE = _definition("cbr.statistics.calculate_share", S.CALCULATE, C.CalculateShareRequest, StatisticsDataset,
    (InputPort("dataset", DATASET, "dataset"),), (OutputPort("dataset", DATASET),),
    parameters=("numerator_metric", "denominator_metric", "release_ids"),
    summary="Calculate an explicitly selected share only when subject, period, units and perimeter agree.")
BUILD_VIEW = _definition("cbr.statistics.build_view", S.VIEW, C.BuildViewRequest, StatisticsView,
    (InputPort("dataset", DATASET, "dataset"),), (OutputPort("view", VIEW),),
    parameters=("series_ids", "metric_ids", "release_ids", "title"),
    summary="Prepare a selected presentation with its complete source-version vector and qualifications.")
RENDER_VIEW = _definition("cbr.statistics.render_view", S.RENDER, C.RenderViewRequest, Representation,
    (InputPort("view", VIEW, "view"),),
    (OutputPort("representation", DataContract("cbr.statistics.product", 1, DataRole.PRODUCTS)),), parameters=("format",),
    summary="Render a prepared or restored view to CSV or XLSX without reading or calculating source data.")
DATASET_SNAPSHOT = _definition("cbr.statistics.dataset_snapshot", S.INTEGRATE, C.DatasetRequest, DatasetSnapshot,
    (InputPort("dataset", DATASET, "dataset"),), (OutputPort("snapshot", _SNAPSHOT),),
    summary="Encode admitted observations, mapping edition, diagnostics and complete input versions.")
READ_DATASET_SNAPSHOT = _definition("cbr.statistics.read_dataset_snapshot", S.INTEGRATE, C.ReadSnapshotRequest, StatisticsDataset,
    (InputPort("snapshot", _SNAPSHOT, "snapshot"),), (OutputPort("dataset", DATASET),),
    summary="Restore exact integrated observations without original files or parsing dependencies.")
VIEW_SNAPSHOT = _definition("cbr.statistics.view_snapshot", S.VIEW, C.ViewRequest, DatasetSnapshot,
    (InputPort("view", VIEW, "view"),), (OutputPort("snapshot", _SNAPSHOT),),
    summary="Expose complete prepared view tables for a caller-selected dataset adapter.")
READ_VIEW_SNAPSHOT = _definition("cbr.statistics.read_view_snapshot", S.VIEW, C.ReadSnapshotRequest, StatisticsView,
    (InputPort("snapshot", _SNAPSHOT, "snapshot"),), (OutputPort("view", VIEW),),
    summary="Restore a prepared view with its exact inputs and rendering profile.")
