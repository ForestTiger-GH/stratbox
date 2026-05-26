"""
regions — выбор итогового списка регионов для витрин по счетам эскроу.

Сейчас поддерживаются режимы:
- latest: порядок регионов из последней доступной даты;
- custom: пользователь передает свой список регионов.

Место под будущее расширение:
- registry: порядок регионов из отдельного реестра stratbox.registries.
"""

from __future__ import annotations

import pandas as pd



def resolve_region_order(
    result_df: pd.DataFrame,
    *,
    mode: str = "latest",
    custom_regions: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """
    Возвращает итоговый порядок регионов для сводных таблиц.
    """
    normalized_mode = str(mode).strip().lower()

    if normalized_mode == "custom":
        if not custom_regions:
            raise ValueError("custom_regions is required when regions_mode='custom'")
        return list(dict.fromkeys([str(x) for x in custom_regions]))

    if normalized_mode == "registry":
        raise NotImplementedError(
            "regions_mode='registry' is reserved for future integration with regions registry"
        )

    if normalized_mode != "latest":
        raise ValueError(f"Unsupported regions_mode: {mode}")

    if result_df.empty:
        return []

    last_date = result_df["Дата"].max()
    region_order = result_df.loc[result_df["Дата"] == last_date, "Регион"].tolist()
    return list(dict.fromkeys([str(x) for x in region_order]))


__all__ = ["resolve_region_order"]
