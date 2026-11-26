"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations
from stratbox.shared.identity import ByteIdentity

from dataclasses import dataclass

from stratbox.shared.data.source_context import SourceUse

from stratbox.shared.data.values import EncodedProduct, fingerprint

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
    evidence: object | None = None
    source_uses: tuple[SourceUse, ...] = ()


@dataclass(frozen=True, slots=True)
class SorsWorkbookResult:
    representation: EncodedProduct
    sheet_names: tuple[str, ...]
    sheet_count: int


@dataclass(frozen=True)
class SorsViewPack:
    """Prepared sheets, including audit tables, with no live solver dependency."""
    tables: tuple[tuple[str, pd.DataFrame], ...]
    source_identity: ByteIdentity | None = None
    evidence: object | None = None
    source_uses: tuple[SourceUse, ...] = ()

    @property
    def fingerprint(self):
        from stratbox.shared.data.tables import table_identity
        from stratbox.shared.data.source_context import source_use_value
        return fingerprint((table_identity(self.tables, allow_infinite=True),
            self.source_identity, tuple(source_use_value(use) for use in self.source_uses)))
