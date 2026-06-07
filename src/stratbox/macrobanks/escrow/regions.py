"""
regions — выбор итогового списка строк для витрин по счетам эскроу.

Режимы:
- latest: порядок строк из последнего распарсенного файла;
- custom: пользователь передает свой список строк.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.escrow.contracts import ParsedEscrowFile



def resolve_region_order(
    result_df: pd.DataFrame,
    *,
    parsed_files: list[ParsedEscrowFile] | tuple[ParsedEscrowFile, ...] | None = None,
    mode: str = "latest",
    custom_regions: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Возвращает итоговый порядок строк для сводных таблиц."""
    normalized_mode = str(mode).strip().lower()

    if normalized_mode == "custom":
        if not custom_regions:
            raise ValueError("custom_regions is required when regions_mode='custom'")
        return list(dict.fromkeys([str(x) for x in custom_regions]))

    if normalized_mode != "latest":
        raise ValueError(f"Unsupported regions_mode: {mode}")

    if parsed_files:
        parsed_list = list(parsed_files)
        latest = sorted(parsed_list, key=lambda item: item.file_date or "", reverse=True)[0]
        rows_df = latest.df_rows.sort_values("display_order")
        return rows_df["Регион"].astype(str).tolist()

    if result_df.empty:
        return []

    last_date = result_df["Дата"].max()
    slice_df = result_df.loc[result_df["Дата"] == last_date].copy()
    if "display_order" in slice_df.columns:
        slice_df = slice_df.sort_values("display_order")
    return list(dict.fromkeys([str(x) for x in slice_df["Регион"].tolist()]))


__all__ = ["resolve_region_order"]
