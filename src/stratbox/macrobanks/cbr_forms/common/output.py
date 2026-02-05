"""
Модуль формирует и экспортирует выходные файлы внутри задачи cbr_forms.

Универсален для всех форм внутри macrobanks/cbr_forms.
"""

from __future__ import annotations

import pandas as pd
from stratbox.base import ioapi as ia


def export_excel(path: str, df: pd.DataFrame) -> None:
    """
    Экспортирует DataFrame в Excel через stratbox ioapi.
    """
    ia.excel.write_df(path, df)
    print(f"[OK] Exported: {path}")


def make_and_export_wide(
    out_path: str,
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    indicator_order: dict[str, int] | None = None,
    date_col: str = "Дата",
    bank_col: str = "Банк",
    indicator_col: str = "Показатель",
    value_col: str = "Значение",
) -> pd.DataFrame:
    """
    Собирает wide-таблицу и экспортирует её в Excel.
    Возвращает wide_df (чтобы можно было посмотреть в ноутбуке).
    """
    from stratbox.macrobanks.cbr_forms.common.wide import build_wide_table

    wide_df = build_wide_table(
        df_long=df_long,
        df_banks=df_banks,
        indicator_order=indicator_order,
        date_col=date_col,
        bank_col=bank_col,
        indicator_col=indicator_col,
        value_col=value_col,
    )
    export_excel(out_path, wide_df)
    return wide_df
