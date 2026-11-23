"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations
from stratbox.shared.identity import ByteIdentity

from dataclasses import dataclass

from stratbox.shared.data.datasets import ComputationReceipt

from stratbox.shared.data.representation import Representation

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class SorsPivotResult:
    table: pd.DataFrame
    orientation: str
    selected_region_code: str | None
    selected_region_name: str | None
    selected_class_code: str | None
    metrics: tuple[str, ...]
    source_rows: int
    output_rows: int
    identified_cells: int
    unidentified_cells: int
    evidence: ComputationReceipt | None = None


@dataclass(frozen=True, slots=True)
class SorsWorkbookResult:
    representation: Representation
    sheet_names: tuple[str, ...]
    sheet_count: int


@dataclass(frozen=True)
class SorsViewPack:
    """Prepared sheets, including audit tables, with no live solver dependency."""
    tables: tuple[tuple[str, pd.DataFrame], ...]
    source_identity: ByteIdentity | None = None
    profile_id: str = "cbr.sors.views.v1"
    evidence: ComputationReceipt | None = None
