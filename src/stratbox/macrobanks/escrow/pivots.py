"""
pivots — построение сводных матриц по каждому показателю счетов эскроу.

Результат:
- для каждого показателя отдельная таблица вида регионы × даты.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from stratbox.macrobanks.escrow.parser import ParsedEscrowFile
from stratbox.macrobanks.escrow.regions import resolve_region_order



def resolve_indicator_order(parsed_files: Iterable[ParsedEscrowFile]) -> list[str]:
    """
    Возвращает порядок показателей по последнему корректно датированному файлу.

    Если даты извлечь не удалось, используется последний файл из списка.
    """
    parsed_list = list(parsed_files)
    if not parsed_list:
        return []

    dated = [item for item in parsed_list if item.file_date]
    if dated:
        latest = sorted(dated, key=lambda item: item.file_date or "", reverse=True)[0]
        return list(dict.fromkeys(latest.indicators_order))

    return list(dict.fromkeys(parsed_list[-1].indicators_order))



def build_escrow_pivot(
    result_df: pd.DataFrame,
    indicator: str,
    *,
    region_order: list[str],
    date_order: list[str],
) -> pd.DataFrame:
    """Строит сводную матрицу по одному показателю: регионы × даты."""
    df_ind = result_df.loc[result_df["Показатель"] == indicator].copy()
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
) -> tuple[dict[str, pd.DataFrame], list[str], list[str], list[str]]:
    """
    Возвращает:
    - pivots: словарь {показатель -> DataFrame}
    - indicators_order: порядок листов/показателей
    - region_order
    - date_order
    """
    if result_df.empty:
        return {}, [], [], []

    date_order = sorted([str(x) for x in result_df["Дата"].dropna().unique().tolist()])
    region_order = resolve_region_order(
        result_df,
        mode=regions_mode,
        custom_regions=custom_regions,
    )

    if parsed_files is not None:
        indicators_order = resolve_indicator_order(parsed_files)
    else:
        indicators_order = sorted([str(x) for x in result_df["Показатель"].dropna().unique().tolist()])

    pivots: dict[str, pd.DataFrame] = {}
    for indicator in indicators_order:
        pivots[indicator] = build_escrow_pivot(
            result_df,
            indicator,
            region_order=region_order,
            date_order=date_order,
        )

    return pivots, indicators_order, region_order, date_order


__all__ = [
    "build_escrow_pivot",
    "build_escrow_pivots",
    "resolve_indicator_order",
]
