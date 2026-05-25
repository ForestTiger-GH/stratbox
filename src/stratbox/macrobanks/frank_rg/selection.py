"""
Отбор актуальных файлов Frank RG по семействам.

На входе используется уже размеченный каталог.
На выходе остается по одному наиболее свежему файлу на семейство.
"""

from __future__ import annotations

import pandas as pd


def select_latest_frank_rg_files(catalog_df: pd.DataFrame) -> pd.DataFrame:
    """Выбирает наиболее свежий файл по каждому распознанному семейству."""
    if catalog_df is None or catalog_df.empty:
        return pd.DataFrame(
            columns=[
                "family_code",
                "family_name",
                "parser_group",
                "parser_key",
                "period_mode",
                "period_date",
                "week_no",
                "path",
                "file_name",
                "selection_key",
                "selection_reason",
            ]
        )

    df = catalog_df.copy()
    df = df[df["is_valid"] == True].copy()
    df = df[df["family_code"].notna()].copy()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "family_code",
                "family_name",
                "parser_group",
                "parser_key",
                "period_mode",
                "period_date",
                "week_no",
                "path",
                "file_name",
                "selection_key",
                "selection_reason",
            ]
        )

    # Для отбора свежести сначала сортируется дата периода,
    # а для недельных файлов дополнительным ключом выступает номер недели.
    df["_week_no_rank"] = df["week_no"].fillna(0).astype(int)
    df = df.sort_values(
        by=["family_code", "period_date", "_week_no_rank", "file_name"],
        ascending=[True, False, False, False],
        na_position="last",
    )

    latest = df.groupby("family_code", as_index=False).head(1).copy()
    latest["selection_key"] = latest.apply(
        lambda row: f"date={row['period_date'].date().isoformat()}|week={int(row['_week_no_rank'])}",
        axis=1,
    )
    latest["selection_reason"] = latest.apply(
        lambda row: (
            "latest_weekly_period_by_name"
            if row["period_mode"] == "weekly"
            else "latest_period_date_by_name"
        ),
        axis=1,
    )

    latest = latest[
        [
            "family_code",
            "family_name",
            "parser_group",
            "parser_key",
            "period_mode",
            "period_date",
            "week_no",
            "path",
            "file_name",
            "selection_key",
            "selection_reason",
        ]
    ].reset_index(drop=True)
    return latest
