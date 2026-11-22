"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import (
    BuildEscrowViewsRequest,
    DiscoverEscrowRequest,
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    EscrowPivotPack,
    EscrowSourceLink,
    ParseEscrowRequest,
    ParsedEscrowFile, EscrowDataset, IntegrateEscrowRequest, EscrowFlakeSnapshotRequest,
    EscrowDatasetSnapshotRequest, EscrowViewSnapshotRequest, ReadEscrowSnapshotRequest,
)

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)

DISCOVER = OperationDefinition(
    "cbr.escrow.discover",
    1,
    "cbr-escrow-index-1",
    DiscoverEscrowRequest,
    tuple,
    optional_capabilities=frozenset({"http"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Discover escrow source links from a supplied or acquired index.",
        inputs=(
            InputPort(
                "index",
                DataContract("cbr.escrow.index_material", 1, DataRole.ORIGINALS),
                path="index",
                required=False,
                alternatives=(DataContract("material.payload"), DataContract("source.payload", 1, DataRole.ORIGINALS)),
            ),
        ),
        outputs=(OutputPort("sources", DataContract("cbr.escrow.index", 1, None)),),
    ),
)

ACQUIRE = OperationDefinition(
    "cbr.escrow.acquire",
    1,
    "cbr-escrow-source-1",
    EscrowSourceLink,
    AcquiredSource,
    frozenset({"http"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire an official escrow XLSX or historical HTML original.",
        inputs=(InputPort("source", DataContract("cbr.escrow.source", 1, None)),),
        outputs=(
            OutputPort(
                "source",
                DataContract("cbr.escrow.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.escrow",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="payload",
            ),
        ),
    ),
)

PARSE = OperationDefinition(
    "cbr.escrow.parse",
    3,
    "cbr-escrow-xlsx-flake-1",
    ParseEscrowRequest,
    ParsedEscrowFile,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract an escrow workbook with source-local dimensions and evidence.",
        inputs=(
            InputPort(
                "source",
                DataContract("cbr.escrow.original", 1, DataRole.ORIGINALS),
                path="payload",
                alternatives=(DataContract("material.payload"), DataContract("source.payload", 1, DataRole.ORIGINALS)),
            ),
        ),
        outputs=(
            OutputPort(
                "file", DataContract("cbr.escrow.parsed_file", 2, DataRole.EXTRACTS)
            ),
        ),
        parameters=("source_name", "as_of"),
    ),
)

HISTORY = OperationDefinition(
    "cbr.escrow.build_history",
    3,
    "cbr-escrow-history-3",
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    partial_allowed=True,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE),
        composition=True,
        summary="Parse supplied escrow sources and construct their history.",
        inputs=(
            InputPort(
                "sources",
                DataContract("cbr.escrow.parse_requests", 1, DataRole.ORIGINALS),
                path="sources",
            ),
        ),
        outputs=(
            OutputPort(
                "history", DataContract("cbr.escrow.history", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("continue_on_error",),
    ),
)

VIEWS = OperationDefinition(
    "cbr.escrow.build_views",
    3,
    "cbr-escrow-views-2",
    BuildEscrowViewsRequest,
    EscrowPivotPack,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.VIEW,),
        summary="Construct escrow presentation views from supplied history.",
        inputs=(
            InputPort(
                "history",
                DataContract("cbr.escrow.history", 1, DataRole.EXTRACTS),
                path="history",
                alternatives=(DataContract("cbr.escrow.dataset", 1, DataRole.INTEGRATED),),
            ),
        ),
        outputs=(
            OutputPort("views", DataContract("cbr.escrow.views", 1, DataRole.PRODUCTS)),
        ),
        parameters=("view",),
    ),
)

RENDER = OperationDefinition(
    "cbr.escrow.render_workbook",
    2,
    "cbr-escrow-xlsx-2",
    EscrowPivotPack,
    Representation,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render supplied escrow pivots into workbook bytes.",
        inputs=(
            InputPort("views", DataContract("cbr.escrow.views", 1, DataRole.PRODUCTS)),
        ),
        outputs=(
            OutputPort(
                "workbook", DataContract("cbr.escrow.workbook", 1, DataRole.PRODUCTS)
            ),
        ),
    ),
)


INTEGRATE = OperationDefinition(
    "cbr.escrow.integrate_flakes", 1, "cbr-escrow-integration-1", IntegrateEscrowRequest, EscrowDataset,
    limits=_TABLES, processing=OperationSemantics(
        stages=(ProcessingStage.INTEGRATE,),
        inputs=(InputPort("flakes", DataContract("cbr.escrow.flakes", 1, DataRole.EXTRACTS), path="flakes"),),
        outputs=(OutputPort("dataset", DataContract("cbr.escrow.dataset", 1, DataRole.INTEGRATED)),),
        parameters=("coverage",), summary="Integrate admitted publication flakes with explicit duplicate and edition checks.",
    ),
)


def _snapshot_definition(operation, request_type, source_name, source_contract, snapshot_contract):
    return OperationDefinition(
        operation, 1, "cbr-escrow-snapshot-1", request_type, DatasetSnapshot, limits=_TABLES,
        processing=OperationSemantics(stages=(ProcessingStage.PRESERVE,),
            inputs=(InputPort(source_name, source_contract, path=source_name),),
            outputs=(OutputPort("snapshot", snapshot_contract), OutputPort("dataset", DataContract("dataset.snapshot"))),
            parameters=("dataset_id", "version_id"), summary="Encode a complete escrow value for any logical dataset adapter."),
    )


def _read_definition(operation, result_type, name, result_contract, snapshot_contract):
    return OperationDefinition(
        operation, 1, "cbr-escrow-snapshot-1", ReadEscrowSnapshotRequest, result_type, limits=_TABLES,
        processing=OperationSemantics(stages=(ProcessingStage.READ_EXTRACT,),
            inputs=(InputPort("snapshot", snapshot_contract, path="snapshot", alternatives=(DataContract("dataset.snapshot"),)),),
            outputs=(OutputPort(name, result_contract),),
            summary="Validate complete escrow snapshot components and restore the domain value."),
    )


FLAKE_SNAPSHOT = _snapshot_definition("cbr.escrow.flake_snapshot", EscrowFlakeSnapshotRequest, "flake",
    DataContract("cbr.escrow.parsed_file", 2, DataRole.EXTRACTS), DataContract("cbr.escrow.flake.snapshot", 1, DataRole.EXTRACTS))
READ_FLAKE_SNAPSHOT = _read_definition("cbr.escrow.read_flake_snapshot", ParsedEscrowFile, "file",
    DataContract("cbr.escrow.parsed_file", 2, DataRole.EXTRACTS), DataContract("cbr.escrow.flake.snapshot", 1, DataRole.EXTRACTS))
DATASET_SNAPSHOT = _snapshot_definition("cbr.escrow.dataset_snapshot", EscrowDatasetSnapshotRequest, "dataset",
    DataContract("cbr.escrow.dataset", 1, DataRole.INTEGRATED), DataContract("cbr.escrow.dataset.snapshot", 1, DataRole.INTEGRATED))
READ_DATASET_SNAPSHOT = _read_definition("cbr.escrow.read_dataset_snapshot", EscrowDataset, "dataset",
    DataContract("cbr.escrow.dataset", 1, DataRole.INTEGRATED), DataContract("cbr.escrow.dataset.snapshot", 1, DataRole.INTEGRATED))
VIEW_SNAPSHOT = _snapshot_definition("cbr.escrow.view_snapshot", EscrowViewSnapshotRequest, "view",
    DataContract("cbr.escrow.views", 1, DataRole.PRODUCTS), DataContract("cbr.escrow.view.snapshot", 1, DataRole.PRODUCTS))
READ_VIEW_SNAPSHOT = _read_definition("cbr.escrow.read_view_snapshot", EscrowPivotPack, "views",
    DataContract("cbr.escrow.views", 1, DataRole.PRODUCTS), DataContract("cbr.escrow.view.snapshot", 1, DataRole.PRODUCTS))
