"""
Модуль собирает wide-таблицы вида:
  Показатель | Банк | <даты...>

Это специфично под отчётные формы (macrobanks/cbr_forms),
поэтому вынесено внутри задачи.
"""

from __future__ import annotations

import pandas as pd


def build_wide_table(
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    indicator_order: dict[str, int] | None = None,
    date_col: str = "Дата",
    bank_col: str = "Банк",
    indicator_col: str = "Показатель",
    value_col: str = "Значение",
) -> pd.DataFrame:
    """
    Строит wide-таблицу:
      - строки: (Показатель, Банк)
      - колонки: даты
      - сортировка банков: df_banks.sort
      - сортировка показателей: indicator_order (если задан)

    Ожидается, что df_banks содержит:
      - bank
      - sort
    """
    if len(df_long) == 0:
        raise RuntimeError("df_long is empty; cannot build wide table.")

    # список дат в правильном порядке
    date_cols = sorted(df_long[date_col].unique().tolist(), key=lambda s: pd.to_datetime(s, dayfirst=True))
    out_cols = [indicator_col, bank_col] + date_cols

    df_out = pd.DataFrame(columns=out_cols)

    bank_sort = {str(r["bank"]): int(r["sort"]) for _, r in df_banks.iterrows()}

    indicators = df_long[indicator_col].dropna().astype(str).unique().tolist()
    indicators = sorted(indicators, key=lambda x: indicator_order.get(x, 999) if indicator_order else x)

    banks = df_banks["bank"].astype(str).tolist()

    for ind in indicators:
        for bank in banks:
            sub = df_long[(df_long[indicator_col] == ind) & (df_long[bank_col] == bank)].copy()

            row = {indicator_col: ind, bank_col: bank}
            for dc in date_cols:
                m = sub[sub[date_col] == dc]
                row[dc] = m[value_col].iloc[0] if len(m) else ""
            df_out.loc[len(df_out)] = row

    # сортировка строк
    df_out["_bank_sort"] = df_out[bank_col].map(bank_sort).fillna(9999).astype(int)
    if indicator_order:
        df_out["_ind_sort"] = df_out[indicator_col].map(indicator_order).fillna(999).astype(int)
        df_out = df_out.sort_values(["_ind_sort", "_bank_sort"]).drop(columns=["_ind_sort", "_bank_sort"]).reset_index(drop=True)
    else:
        df_out = df_out.sort_values(["_bank_sort"]).drop(columns=["_bank_sort"]).reset_index(drop=True)

    return df_out
