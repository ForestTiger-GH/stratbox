"""Source cell data, independent clean tables and explicit economic mappings."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.representation import Representation


@dataclass(frozen=True, slots=True)
class Cell:
    sheet: str
    row: int
    column: int
    kind: str
    value: str
    number_format: str = ""
    cached: str | None = None


@dataclass(frozen=True, slots=True)
class Sheet:
    name: str
    rows: int
    columns: int
    cells: tuple[Cell, ...]


@dataclass(frozen=True, slots=True)
class TableExtract:
    family_id: str
    source_id: str
    source_identity: ByteIdentity
    format: str
    sheets: tuple[Sheet, ...]
    member: str | None = None
    coverage: str = "nonempty_cells"


@dataclass(frozen=True, slots=True)
class ExtractRequest:
    family_id: str
    payload: SourcePayload
    format: str
    member: str | None = None
    selected_sheets: tuple[str, ...] = ()
    max_cells: int = 150_000
    csv_encoding: str = "utf-8-sig"


@dataclass(frozen=True, slots=True)
class CellChange:
    sheet: str
    row: int
    column: int
    before: Cell | None
    after: Cell | None


@dataclass(frozen=True, slots=True)
class SheetChange:
    sheet: str
    before_rows: int | None
    before_columns: int | None
    after_rows: int | None
    after_columns: int | None


@dataclass(frozen=True, slots=True)
class TableComparison:
    family_id: str
    before_identity: ByteIdentity
    after_identity: ByteIdentity
    changes: tuple[CellChange, ...]
    layout_changes: tuple[SheetChange, ...] = ()
    layer: Literal["source_cells"] = "source_cells"


@dataclass(frozen=True, slots=True)
class CompareRequest:
    before: TableExtract
    after: TableExtract
    max_changes: int = 100_000


@dataclass(frozen=True, slots=True)
class ValidateRequest:
    extract: TableExtract


@dataclass(frozen=True, slots=True)
class Validation:
    family_id: str
    cells: int
    sheets: int
    formulas_without_cache: int
    empty_sheets: tuple[str, ...]
    level: Literal["structural_only"] = "structural_only"


@dataclass(frozen=True, slots=True)
class RenderRequest:
    extract: TableExtract


@dataclass(frozen=True, slots=True)
class MetricBinding:
    """Explicit, reviewed mapping from a source cell to an economic value."""
    sheet: str
    row: int
    column: int
    metric_id: str
    period_id: str
    value_basis: str  # e.g. ytd, period_flow, stock, percent
    unit: str
    geography_id: str = "RU"


@dataclass(frozen=True, slots=True)
class MetricObservation:
    metric_id: str
    period_id: str
    geography_id: str
    value: str
    value_basis: str
    unit: str
    sheet: str
    row: int
    column: int


@dataclass(frozen=True, slots=True)
class MappedObservations:
    family_id: str
    source_identity: ByteIdentity
    observations: tuple[MetricObservation, ...]


@dataclass(frozen=True, slots=True)
class MapRequest:
    extract: TableExtract
    bindings: tuple[MetricBinding, ...]


@dataclass(frozen=True, slots=True)
class SerializeRequest:
    extract: TableExtract


@dataclass(frozen=True, slots=True)
class ReadRepresentationRequest:
    representation: Representation


@dataclass(frozen=True, slots=True)
class FlakeColumn:
    source_column: int
    original_header: str
    period_id: str


@dataclass(frozen=True, slots=True)
class FlakeRow:
    source_row: int
    code: str
    indicator: str
    values: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class FlakeTable:
    family_id: str
    source_id: str
    original_identity: ByteIdentity
    sheet_name: str
    frequency: Literal["monthly", "quarterly", "annual"]
    value_basis: Literal["ytd", "annual", "stock"]
    columns: tuple[FlakeColumn, ...]
    rows: tuple[FlakeRow, ...]
    method_version: str = "minfin.flake.v1"
    unit_hint: str = "billion_rub"  # per-row units in NWF may differ; only headline metrics use RUB

    @property
    def latest_period(self) -> str:
        return self.columns[-1].period_id


@dataclass(frozen=True, slots=True)
class BuildFlakeRequest:
    extract: TableExtract
    source_id: str
    selected_sheet: str | None = None


@dataclass(frozen=True, slots=True)
class RenderFlakeRequest:
    flake: FlakeTable
