"""
Модуль собирает Excel-friendly wide-таблицы отчетных форм Банка России.

Внутренняя идентичность строки строится по стабильному ``IndicatorId``, а не
по русскому названию показателя. Поэтому одинаковые названия в форме 802 не
создают коллизий при развороте таблицы.
"""

from __future__ import annotations

import pandas as pd


def build_wide_table(
    df_long: pd.DataFrame,
    df_banks: pd.DataFrame,
    indicator_order: dict[str, int] | None = None,
    date_col: str = "Дата",
    bank_col: str = "Банк",
    indicator_id_col: str = "IndicatorId",
    code_col: str = "Код",
    indicator_col: str = "Показатель",
    value_col: str = "Значение",
) -> pd.DataFrame:
    """
    Функция разворачивает canonical long в таблицу по датам.

    Строка wide идентифицируется парой ``IndicatorId + Банк``. Код и русское
    название используются только как отображаемые атрибуты.
    """
    if len(df_long) == 0:
        raise RuntimeError("df_long is empty; cannot build wide table.")

    required = {date_col, bank_col, indicator_id_col, indicator_col, value_col}
    missing = required - set(df_long.columns)
    if missing:
        raise RuntimeError(f"df_long missing required wide columns: {sorted(missing)}")

    work = df_long.copy()
    if code_col not in work.columns:
        work[code_col] = ""

    duplicate_mask = work.duplicated(
        subset=[indicator_id_col, bank_col, date_col],
        keep=False,
    )
    if duplicate_mask.any():
        sample = work.loc[
            duplicate_mask,
            [indicator_id_col, bank_col, date_col],
        ].head(10)
        raise RuntimeError(f"Duplicate long keys before wide pivot: {sample.to_dict('records')}")

    date_cols = sorted(
        work[date_col].astype(str).unique().tolist(),
        key=lambda value: pd.to_datetime(value, dayfirst=True),
    )

    meta = (
        work[[indicator_id_col, code_col, indicator_col]]
        .drop_duplicates(subset=[indicator_id_col], keep="first")
        .set_index(indicator_id_col)
    )

    indicator_ids = meta.index.astype(str).tolist()
    if indicator_order:
        indicator_ids = sorted(
            indicator_ids,
            key=lambda value: (indicator_order.get(value, 10**9), value),
        )
    else:
        indicator_ids = sorted(indicator_ids)

    banks = df_banks.sort_values("sort", kind="stable")["bank"].astype(str).tolist()
    row_index = pd.MultiIndex.from_product(
        [indicator_ids, banks],
        names=[indicator_id_col, bank_col],
    )

    matrix = work.set_index([indicator_id_col, bank_col, date_col])[value_col].unstack(date_col)
    matrix = matrix.reindex(index=row_index, columns=date_cols)
    matrix = matrix.where(matrix.notna(), "")

    result = matrix.reset_index()
    result.insert(0, indicator_col, result[indicator_id_col].map(meta[indicator_col]).fillna(""))
    result.insert(0, code_col, result[indicator_id_col].map(meta[code_col]).fillna(""))

    # Stable ID остается внутренним ключом. В Excel выводятся код, название и банк.
    result = result.drop(columns=[indicator_id_col])
    if not result[code_col].astype(str).str.strip().ne("").any():
        result = result.drop(columns=[code_col])

    return result.reset_index(drop=True)
