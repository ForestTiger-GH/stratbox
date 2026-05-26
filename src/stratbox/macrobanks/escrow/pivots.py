"""
pivots — построение сводных матриц по каждому показателю счетов эскроу.

Итог:
- для каждого показателя отдельная таблица вида строки витрины × даты;
- порядок строк берется из последнего файла и сохраняет структуру ФО -> регионы -> итог по РФ;
- порядок показателей берется из стандартного словаря.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from stratbox.macrobanks.escrow.columns import get_output_indicator_specs
from stratbox.macrobanks.escrow.models import EscrowIndicatorSpec, ParsedEscrowFile
from stratbox.macrobanks.escrow.regions import resolve_region_order


def resolve_indicator_order(parsed_files: Iterable[ParsedEscrowFile]) -> list[EscrowIndicatorSpec]:
    """Возвращает порядок показателей, реально встреченных в наборе файлов."""
    parsed_list = list(parsed_files)
    if not parsed_list:
        return []

    present_codes: set[str] = set()
    for item in parsed_list:
        for resolved in item.resolved_columns:
            if resolved.spec.is_output:
                present_codes.add(resolved.spec.code)

    ordered_specs = [spec for spec in get_output_indicator_specs() if spec.code in present_codes]
    return ordered_specs


def build_escrow_pivot(
    result_df: pd.DataFrame,
    indicator_code: str,
    *,
    region_order: list[str],
    date_order: list[str],
) -> pd.DataFrame:
    """Строит сводную матрицу по одному показателю: строки витрины × даты."""
    df_ind = result_df.loc[result_df["indicator_code"] == indicator_code].copy()
    pivot = df_ind.pivot_table(index="Регион", columns="Дата", values="Значение")
    pivot = pivot.reindex(region_order)
    pivot = pivot.reindex(columns=date_order)
    return pivot


def build_escrow_pivots(
    result_df: pd.DataFrame,
    *,
    parsed_files: Iterable[ParsedEscrowFile] | None = None,
    regions_mode: str = "latest",
    custom_regions: list[str] | tuple[str, ...] | None = None,
) -> tuple[dict[str, pd.DataFrame], list[EscrowIndicatorSpec], list[str], list[str]]:
    """
    Возвращает:
    - pivots: словарь {indicator_code -> DataFrame}
    - indicator_specs: порядок листов/показателей
    - region_order
    - date_order
    """
    if result_df.empty:
        return {}, [], [], []

    date_order = sorted([str(x) for x in result_df["Дата"].dropna().unique().tolist()])
    parsed_list = list(parsed_files) if parsed_files is not None else None
    region_order = resolve_region_order(
        result_df,
        parsed_files=parsed_list,
        mode=regions_mode,
        custom_regions=custom_regions,
    )

    if parsed_list is not None:
        indicator_specs = resolve_indicator_order(parsed_list)
    else:
        raise ValueError("parsed_files is required to build escrow pivots reliably")

    pivots: dict[str, pd.DataFrame] = {}
    for spec in indicator_specs:
        pivots[spec.code] = build_escrow_pivot(
            result_df,
            spec.code,
            region_order=region_order,
            date_order=date_order,
        )

    return pivots, indicator_specs, region_order, date_order


__all__ = [
    "build_escrow_pivot",
    "build_escrow_pivots",
    "resolve_indicator_order",
]
