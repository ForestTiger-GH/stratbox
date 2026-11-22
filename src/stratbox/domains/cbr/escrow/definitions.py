"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import BuildEscrowViewsRequest, DiscoverEscrowRequest, EscrowHistoryBuildRequest, EscrowHistoryResult, EscrowPivotPack, EscrowSourceLink, ParseEscrowRequest, ParsedEscrowFile

_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)

DISCOVER = OperationDefinition(
    "cbr.escrow.discover", 1, "cbr-escrow-index-1", DiscoverEscrowRequest, tuple,
    optional_capabilities=frozenset({"http"}),
)

ACQUIRE = OperationDefinition(
    "cbr.escrow.acquire",
    1,
    "cbr-escrow-source-1",
    EscrowSourceLink,
    AcquiredSource,
    frozenset({"http"}),
)

PARSE = OperationDefinition(
    "cbr.escrow.parse", 2, "cbr-escrow-layout-2", ParseEscrowRequest, ParsedEscrowFile, limits=_TABLES
)

HISTORY = OperationDefinition(
    "cbr.escrow.build_history",
    2,
    "cbr-escrow-history-2",
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    partial_allowed=True,
    limits=_TABLES,
)

VIEWS = OperationDefinition(
    "cbr.escrow.build_views",
    2,
    "cbr-escrow-views-1",
    BuildEscrowViewsRequest,
    EscrowPivotPack,
    limits=_TABLES,
)

RENDER = OperationDefinition(
    "cbr.escrow.render_workbook",
    2,
    "cbr-escrow-xlsx-1",
    EscrowPivotPack,
    Representation,
    limits=_TABLES,
)

