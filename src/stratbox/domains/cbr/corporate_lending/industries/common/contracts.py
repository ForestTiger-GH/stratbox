"""Shared industry-family contracts for Bank of Russia stock and flow series.

Only genuinely identical dimensions and result shapes live here. Physical
source profiles, publication periods and operation identities stay independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Mapping

from stratbox.shared.data.datasets import ComputationReceipt

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class IndustrySelection:
    """Published industry codes to materialize; None means all published codes."""
    industry_codes: tuple[str, ...] | None = None


IndustryPivotDimension = Literal[
    "report_date",
    "region_code",
    "industry_code",
    "measure",
    "currency_scope",
]


@dataclass(frozen=True, slots=True)
class IndustrySpec:
    """Один опубликованный отраслевой показатель семейства таблиц Банка России."""

    code: str
    canonical_name_ru: str
    parent_code: str | None
    hierarchy_level: int
    order: int


@dataclass(frozen=True, slots=True)
class IndustryRegionSpec:
    """Географическая строка отраслевой публикации Банка России."""

    code: str
    source_name: str
    canonical_name: str
    region_kind: str
    federal_district_name: str | None
    order: int


@dataclass(frozen=True, slots=True)
class IndustryValidationIssue:
    """Отклонение, найденное в структуре или значениях публикации."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    count: int = 1
    details: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class IndustryApkCalculationResult:
    """Результат добавления расчетной отрасли ``АПК`` в поток."""

    industry: IndustrySpec
    source_industry_codes: tuple[str, ...]
    lpk_formula_ru: str
    apk_formula_ru: str
    df_apk: pd.DataFrame
    df_stream: pd.DataFrame
    source_rows_used: int
    groups_calculated: int
    rows_added: int
    evidence: ComputationReceipt | None = None

    @property
    def ok(self) -> bool:
        return self.rows_added > 0 and self.rows_added == len(self.df_apk)


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
