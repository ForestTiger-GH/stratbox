"""Integrated escrow observations with source release and selection evidence."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.cbr.tables.project_finance.contracts import EscrowIndicatorSpec
if TYPE_CHECKING:
    import pandas as pd

@dataclass(frozen=True, slots=True)
class EscrowRelease:
    """One admitted publication and its interpretation profile."""

    period: str
    source_name: str
    source_id: str | None
    original_identity: ByteIdentity
    sheet_name: str
    method_version: str
    unmapped_headers: tuple[str, ...] = ()


@dataclass(frozen=True)
class EscrowDataset:
    """Integrated observations and period-specific row dimensions.

    Publication coverage is distinct from successful processing of the selected
    flakes. No live parsed-file objects are needed to prepare views.
    """

    observations: pd.DataFrame
    rows: pd.DataFrame
    releases: tuple[EscrowRelease, ...]
    indicator_specs: tuple[EscrowIndicatorSpec, ...]
    coverage: SnapshotCoverage
    selection_complete: bool = True
    evidence: ComputationReceipt | None = None

    failures: tuple[tuple[str, str], ...] = ()
    stop_reason: str | None = None
    integration_profile: str = "cbr-escrow-integration-2"
