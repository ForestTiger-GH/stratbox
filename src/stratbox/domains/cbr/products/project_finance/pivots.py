"""A unique-observation pivot helper for already selected product rows."""
from __future__ import annotations
import pandas as pd

def build_escrow_pivot(
    result_df: pd.DataFrame,
    indicator_code: str,
    *,
    region_order: list[str],
    date_order: list[str],
) -> pd.DataFrame:
    """Pivot unique selected observations by geography and reporting date."""
    df_ind = result_df.loc[result_df["indicator_code"] == indicator_code].copy()
    if df_ind.duplicated(["Регион", "Дата"]).any():
        raise ValueError("escrow.duplicate_observation")
    pivot = df_ind.pivot(index="Регион", columns="Дата", values="Значение")
    pivot = pivot.reindex(region_order)
    pivot = pivot.reindex(columns=date_order)
    return pivot
