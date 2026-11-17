"""Shared canonical long schema and memory-efficient aggregation for CBR industry series."""

from __future__ import annotations

from typing import Iterable
import pandas as pd

_CATEGORY_COLUMNS = (
    "series_code",
    "report_date",
    "sheet_code",
    "measure",
    "measure_name_ru",
    "currency_scope",
    "currency_scope_name_ru",
    "unit",
    "unit_name_ru",
    "region_code",
    "region_name",
    "region_source_name",
    "region_kind",
    "federal_district_name",
    "industry_code",
    "industry_name_ru",
    "industry_source_name",
    "industry_parent_code",
    "source_id",
    "source_url",
    "source_name",
    "source_sha256",
    "source_sheet_name",
    "source_sheet_title",
    "source_column",
)

STREAM_COLUMNS = (
    "series_code",
    "report_date",
    "sheet_code",
    "sheet_order",
    "measure",
    "measure_name_ru",
    "currency_scope",
    "currency_scope_name_ru",
    "unit",
    "unit_name_ru",
    "region_code",
    "region_name",
    "region_source_name",
    "region_kind",
    "federal_district_name",
    "region_order",
    "industry_code",
    "industry_name_ru",
    "industry_source_name",
    "industry_parent_code",
    "industry_hierarchy_level",
    "industry_order",
    "value",
    "source_id",
    "source_url",
    "source_name",
    "source_sha256",
    "source_sheet_name",
    "source_sheet_title",
    "source_row",
    "source_column",
)


def optimize_cbr_0105a_debt_corp_stream_dtypes(df_stream: pd.DataFrame) -> pd.DataFrame:
    """Уплотняет измерения потока для полной месячной истории."""
    stream = df_stream.copy()
    for column in _CATEGORY_COLUMNS:
        if column in stream.columns:
            stream[column] = stream[column].astype("category")
    integer_dtypes = {
        "sheet_order": "int8",
        "region_order": "int16",
        "industry_hierarchy_level": "int8",
        "industry_order": "int8",
        "source_row": "int16",
    }
    for column, dtype in integer_dtypes.items():
        if column in stream.columns:
            stream[column] = stream[column].astype(dtype)
    if "value" in stream.columns:
        stream["value"] = pd.array(stream["value"], dtype="Float64")
    return stream


def _ordered_categories(frames: tuple[pd.DataFrame, ...], column: str) -> list[object]:
    categories: list[object] = []
    seen: set[object] = set()
    for frame in frames:
        if column not in frame.columns:
            continue
        series = frame[column]
        values = (
            series.cat.categories.tolist()
            if isinstance(series.dtype, pd.CategoricalDtype)
            else series.dropna().unique().tolist()
        )
        for value in values:
            if pd.isna(value) or value in seen:
                continue
            seen.add(value)
            categories.append(value)
    return categories


def concat_cbr_0105a_debt_corp_streams(
    frames: Iterable[pd.DataFrame],
) -> pd.DataFrame:
    """Объединяет месячные потоки без распаковки категорий в тяжелый ``object``.

    Pandas сохраняет categorical dtype только при одинаковом наборе категорий во
    всех частях. Поэтому категории сначала выравниваются на небольших справочниках,
    а затем выполняется concat.
    """
    frame_tuple = tuple(frame for frame in frames if frame is not None and not frame.empty)
    if not frame_tuple:
        return pd.DataFrame(columns=STREAM_COLUMNS)

    category_dtypes: dict[str, pd.CategoricalDtype] = {}
    for column in _CATEGORY_COLUMNS:
        if any(column in frame.columns for frame in frame_tuple):
            category_dtypes[column] = pd.CategoricalDtype(
                categories=_ordered_categories(frame_tuple, column),
                ordered=False,
            )

    aligned: list[pd.DataFrame] = []
    for frame in frame_tuple:
        current = frame.copy(deep=False)
        for column, dtype in category_dtypes.items():
            if column in current.columns:
                current[column] = current[column].astype(dtype)
        aligned.append(current)

    stream = pd.concat(aligned, ignore_index=True)
    return optimize_cbr_0105a_debt_corp_stream_dtypes(stream)


