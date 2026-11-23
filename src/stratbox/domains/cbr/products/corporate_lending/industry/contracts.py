"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

from stratbox.shared.data.datasets import ComputationReceipt

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


IndustryPivotDimension = Literal[
    "report_date",
    "region_code",
    "industry_code",
    "measure",
    "currency_scope",
]


@dataclass(frozen=True, slots=True)
class IndustryPivotRequest:
    """Запрос на построение набора двумерных таблиц из отфильтрованного потока.

    Все смысловые измерения, которые не назначены строками, столбцами или листами,
    обязаны быть заранее отфильтрованы до одного значения.
    """

    row_dimension: IndustryPivotDimension
    column_dimension: IndustryPivotDimension
    value_columns: tuple[str, ...] = ("value",)
    sheet_dimensions: tuple[IndustryPivotDimension, ...] = ()
    require_complete_stream: bool = True
    max_sheet_count: int = 100


@dataclass(frozen=True)
class IndustryPivotTable:
    """Одна двумерная таблица будущего листа workbook."""

    sheet_key: tuple[tuple[str, object], ...]
    suggested_sheet_name: str
    row_dimension: IndustryPivotDimension
    column_dimension: IndustryPivotDimension
    value_columns: tuple[str, ...]
    df_table: pd.DataFrame
    rows: int
    data_columns: int
    missing_values: int


@dataclass(frozen=True)
class IndustryPivotSetResult:
    """Набор таблиц, построенный одной универсальной pivot-операцией."""

    tables: tuple[IndustryPivotTable, ...]
    row_dimension: IndustryPivotDimension
    column_dimension: IndustryPivotDimension
    value_columns: tuple[str, ...]
    sheet_dimensions: tuple[IndustryPivotDimension, ...]
    fixed_dimensions: tuple[tuple[str, object], ...]
    source_rows: int
    table_count: int
    is_partial: bool
    evidence: ComputationReceipt | None = None

    @property
    def ok(self) -> bool:
        return bool(self.tables)
