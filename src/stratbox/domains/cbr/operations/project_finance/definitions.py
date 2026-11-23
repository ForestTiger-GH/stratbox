"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition


from stratbox.core.limits import ExecutionBudget
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from .contracts import (
    BuildEscrowViewsRequest,
    DiscoverEscrowRequest,
    EscrowHistoryBuildRequest,
    EscrowPivotPack,
    EscrowSourceLink,
    ParseEscrowRequest,
    ParsedEscrowFile, EscrowDataset, IntegrateEscrowRequest, EscrowFlakeSnapshotRequest,
    EscrowDatasetSnapshotRequest, EscrowViewSnapshotRequest, ReadEscrowSnapshotRequest,
)

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)

DISCOVER = _registry_definition('cbr.escrow.discover')

ACQUIRE = _registry_definition('cbr.escrow.acquire')

PARSE = _registry_definition('cbr.escrow.parse')

HISTORY = _registry_definition('cbr.escrow.build_history')

VIEWS = _registry_definition('cbr.escrow.build_views')

RENDER = _registry_definition('cbr.escrow.render_workbook')


INTEGRATE = _registry_definition('cbr.escrow.integrate_flakes')


FLAKE_SNAPSHOT = _registry_definition('cbr.escrow.flake_snapshot')
READ_FLAKE_SNAPSHOT = _registry_definition('cbr.escrow.read_flake_snapshot')
DATASET_SNAPSHOT = _registry_definition('cbr.escrow.dataset_snapshot')
READ_DATASET_SNAPSHOT = _registry_definition('cbr.escrow.read_dataset_snapshot')
VIEW_SNAPSHOT = _registry_definition('cbr.escrow.view_snapshot')
READ_VIEW_SNAPSHOT = _registry_definition('cbr.escrow.read_view_snapshot')


from stratbox.shared.data.observations import ObservationBatch
from .contracts import (AlignEscrowObservationsRequest, CompareEscrowFlakesRequest,
                        EscrowFlakeValidation, EscrowFlakeComparison)

VALIDATE = _registry_definition('cbr.escrow.validate')
COMPARE = _registry_definition('cbr.escrow.compare')
READABLE = _registry_definition('cbr.escrow.readable')
ALIGN = _registry_definition('cbr.escrow.align_observations')
