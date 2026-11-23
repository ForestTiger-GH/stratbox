"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition


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

DISCOVER = _registry_definition('cbr.escrow.discover', 1)

ACQUIRE = _registry_definition('cbr.escrow.acquire', 1)

PARSE = _registry_definition('cbr.escrow.parse', 4)

HISTORY = _registry_definition('cbr.escrow.build_history', 4)

VIEWS = _registry_definition('cbr.escrow.build_views', 4)

RENDER = _registry_definition('cbr.escrow.render_workbook', 3)


INTEGRATE = _registry_definition('cbr.escrow.integrate_flakes', 2)


FLAKE_SNAPSHOT = _registry_definition('cbr.escrow.flake_snapshot', 2)
READ_FLAKE_SNAPSHOT = _registry_definition('cbr.escrow.read_flake_snapshot', 2)
DATASET_SNAPSHOT = _registry_definition('cbr.escrow.dataset_snapshot', 2)
READ_DATASET_SNAPSHOT = _registry_definition('cbr.escrow.read_dataset_snapshot', 2)
VIEW_SNAPSHOT = _registry_definition('cbr.escrow.view_snapshot', 2)
READ_VIEW_SNAPSHOT = _registry_definition('cbr.escrow.read_view_snapshot', 2)


from stratbox.shared.data.observations import ObservationBatch
from .contracts import (AlignEscrowObservationsRequest, CompareEscrowFlakesRequest,
                        EscrowFlakeValidation, EscrowFlakeComparison)

VALIDATE = _registry_definition('cbr.escrow.validate', 1)
COMPARE = _registry_definition('cbr.escrow.compare', 1)
READABLE = _registry_definition('cbr.escrow.readable', 1)
ALIGN = _registry_definition('cbr.escrow.align_observations', 1)
