"""
Отбор актуальных файлов Frank RG по семействам.

На входе используется уже размеченный каталог.
На выходе остается по одному наиболее свежему файлу на семейство.
При равном периоде и неделе приоритет отдаётся внутреннему имени,
которое уже создала сама библиотека.
"""

from __future__ import annotations

import pandas as pd



def select_latest_frank_rg_files(catalog_df: pd.DataFrame) -> pd.DataFrame:
    """Выбирает наиболее свежий файл по каждому распознанному семейству."""
    columns = [
        "family_code",
        "family_name",
        "file_label",
        "parser_group",
        "parser_key",
        "period_mode",
        "period_date",
        "period_date_text",
        "week_no",
        "name_origin",
        "name_priority",
        "path",
        "file_name",
        "extension",
        "selection_key",
        "selection_reason",
    ]

    if catalog_df is None or catalog_df.empty:
        return pd.DataFrame(columns=columns)

    df = catalog_df.copy()
    df = df[df["is_valid"] == True].copy()
    df = df[df["family_code"].notna()].copy()

    if df.empty:
        return pd.DataFrame(columns=columns)

    df["_week_no_rank"] = pd.to_numeric(df["week_no"], errors="coerce").fillna(0).astype(int)
    df["_name_priority_rank"] = df["name_priority"].fillna(0).astype(int)
    df = df.sort_values(
        by=["family_code", "period_date", "_week_no_rank", "_name_priority_rank", "file_name"],
        ascending=[True, False, False, False, False],
        na_position="last",
    )

    latest = df.groupby("family_code", as_index=False).head(1).copy()
    latest["selection_key"] = latest.apply(
        lambda row: (
            f"date={row['period_date'].date().isoformat()}|"
            f"week={int(row['_week_no_rank'])}|"
            f"origin={row['name_origin']}"
        ),
        axis=1,
    )
    latest["selection_reason"] = latest.apply(
        lambda row: (
            "prefer_internal_standard_name_for_same_period"
            if row["name_origin"] == "internal_standard"
            else (
                "latest_weekly_period_by_name"
                if row["period_mode"] == "weekly"
                else "latest_period_date_by_name"
            )
        ),
        axis=1,
    )

    latest = latest[columns].reset_index(drop=True)
    return latest
