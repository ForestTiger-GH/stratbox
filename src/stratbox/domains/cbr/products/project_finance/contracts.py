"""Prepared escrow tables require no source parsing or integration to render."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt
from .profiles import EscrowProductIndicator, EscrowProductProfile, DEFAULT_PRODUCT_PROFILE
if TYPE_CHECKING:
    import pandas as pd

@dataclass(frozen=True, slots=True)
class EscrowViewBuildRequest:
    """Select rows and a presentation profile from an integrated history."""

    regions_mode: Literal["latest", "custom"] = "latest"
    custom_regions: tuple[str, ...] = ()
    require_complete_history: bool = True
    missing_display: Literal["source_token", "blank"] = "source_token"

    profile: EscrowProductProfile = DEFAULT_PRODUCT_PROFILE

@dataclass(frozen=True)
class EscrowPivotPack:
    """Complete prepared tables and presentation settings for workbook rendering."""

    pivots: dict[str, pd.DataFrame]
    indicator_specs: tuple[EscrowProductIndicator, ...]
    region_order: tuple[str, ...]
    date_order: tuple[str, ...]
    evidence: ComputationReceipt | None = None
    source_dataset: ByteIdentity | None = None
    coverage: SnapshotCoverage = SnapshotCoverage("unknown")
    missing_display: str = "source_token"
    row_metadata: tuple[tuple[str, str, str | None], ...] = ()

    product_profile_id: str = "cbr-escrow-regional-history"
    product_profile_version: int = 1
    input_versions: tuple[UsedInputReceipt, ...] = ()
