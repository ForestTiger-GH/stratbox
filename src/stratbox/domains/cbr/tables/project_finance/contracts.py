"""Source-local escrow metrics, parsed cells and publication row identities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.identity import ByteIdentity
if TYPE_CHECKING:
    import pandas as pd

@dataclass(frozen=True, slots=True)
class EscrowIndicatorSpec:
    """Meaning and measurement basis of a published indicator."""
    code: str
    canonical_name: str
    value_kind: str = "number"
    unit: str = "count"
    scale: str = "1"
    quantity_kind: str | None = "count"
    definition_version: str = "cbr-escrow-metrics-1"

    def __post_init__(self):
        from decimal import Decimal
        if (not self.code or not self.canonical_name or self.value_kind not in {"number", "percent"}
                or not self.unit or self.quantity_kind not in {"stock", "flow", "ratio", "index", "count", None}
                or not Decimal(self.scale).is_finite() or Decimal(self.scale) <= 0 or not self.definition_version):
            raise ValueError("escrow.indicator_invalid")

@dataclass(frozen=True)
class ResolvedEscrowColumn:
    """A source column paired with a reviewed metric definition."""

    source_name: str
    source_index: int
    spec: EscrowIndicatorSpec


@dataclass(frozen=True)
class EscrowParsedRow:
    """A source geography row with its published hierarchy and order."""

    source_row_index: int
    display_order: int
    row_kind: str
    entity_name: str
    federal_district_name: str | None
    region_number: int | None


@dataclass(frozen=True)
class ParsedEscrowFile:
    """One source-local escrow table with complete decoded cell evidence."""

    source_name: str
    file_date: str | None
    sheet_name: str
    header_row_index: int
    resolved_columns: list[ResolvedEscrowColumn]
    rows: list[EscrowParsedRow]
    df_rows: pd.DataFrame
    df_long: pd.DataFrame
    evidence: ComputationReceipt | None = None
    unmapped_headers: tuple[str, ...] = ()
    df_cells: pd.DataFrame | None = None
    original_identity: ByteIdentity | None = None
    source_id: str | None = None
    method_version: str = "cbr-escrow-xlsx-flake-2"
