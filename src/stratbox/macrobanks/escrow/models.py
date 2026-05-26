"""
models — внутренние модели домена счетов эскроу.

Модели описывают:
- спецификацию показателя;
- сопоставленный столбец исходного Excel;
- распознанную строку иерархической таблицы;
- результат парсинга одного файла.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class EscrowIndicatorSpec:
    """Спецификация одного показателя из стандартной таблицы ЦБ."""

    code: str
    canonical_name: str
    sheet_code: str
    required_tokens: tuple[str, ...]
    order: int
    value_kind: str = "number"


@dataclass(frozen=True)
class ResolvedEscrowColumn:
    """Сопоставление реального столбца Excel со спецификацией показателя."""

    source_name: str
    source_index: int
    spec: EscrowIndicatorSpec


@dataclass(frozen=True)
class EscrowParsedRow:
    """Распознанная строка таблицы по регионам."""

    source_row_index: int
    display_order: int
    row_kind: str
    entity_name: str
    federal_district_name: str | None
    region_number: int | None


@dataclass(frozen=True)
class ParsedEscrowFile:
    """Результат парсинга одного Excel-файла по счетам эскроу."""

    source_name: str
    file_date: str | None
    sheet_name: str
    header_row_index: int
    resolved_columns: list[ResolvedEscrowColumn]
    rows: list[EscrowParsedRow]
    df_rows: pd.DataFrame
    df_long: pd.DataFrame


__all__ = [
    "EscrowIndicatorSpec",
    "EscrowParsedRow",
    "ParsedEscrowFile",
    "ResolvedEscrowColumn",
]
