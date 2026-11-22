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
    ParsedEscrowFile,
)

from stratbox.shared.data.processing import DataContract, DataRole
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
        summary="Acquire one official escrow workbook.",
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
    2,
    "cbr-escrow-layout-2",
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
                qualifications=frozenset(("source.cbr.escrow",)),
            ),
        ),
        outputs=(
            OutputPort(
                "file", DataContract("cbr.escrow.parsed_file", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("source_name", "as_of"),
    ),
)

HISTORY = OperationDefinition(
    "cbr.escrow.build_history",
    2,
    "cbr-escrow-history-2",
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    partial_allowed=True,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.CALCULATE),
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
    2,
    "cbr-escrow-views-1",
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
    "cbr-escrow-xlsx-1",
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
