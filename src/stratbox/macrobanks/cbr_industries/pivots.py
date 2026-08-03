"""Универсальное построение двумерных таблиц из потока ``01_05_A_Debt_corp``."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
from pandas.api.types import is_numeric_dtype

from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpPivotDimension,
    Cbr0105ADebtCorpPivotRequest,
    Cbr0105ADebtCorpPivotSetResult,
    Cbr0105ADebtCorpPivotTable,
    Cbr0105ADebtCorpStreamResult,
)


CBR_0105A_DEBT_CORP_PIVOT_DIMENSIONS: tuple[Cbr0105ADebtCorpPivotDimension, ...] = (
    "report_date",
    "region_code",
    "industry_code",
    "measure",
    "currency_scope",
)

# Контекстные измерения нельзя назначить осью, но они тоже обязаны быть
# однозначными после внешней фильтрации.
_CONTEXT_DIMENSIONS = ("series_code", "unit")

_TECHNICAL_NUMERIC_COLUMNS = {
    "sheet_order",
    "region_order",
    "industry_hierarchy_level",
    "industry_order",
    "source_row",
}

_DIMENSION_DESCRIPTORS: dict[str, tuple[str, ...]] = {
    "report_date": ("report_date",),
    "region_code": (
        "region_code",
        "region_name",
        "region_kind",
        "federal_district_name",
    ),
    "industry_code": (
        "industry_code",
        "industry_name_ru",
        "industry_parent_code",
        "industry_hierarchy_level",
    ),
    "measure": ("measure", "measure_name_ru"),
    "currency_scope": ("currency_scope", "currency_scope_name_ru"),
}

_DIMENSION_ORDER_COLUMNS: dict[str, str | None] = {
    "report_date": None,
    "region_code": "region_order",
    "industry_code": "industry_order",
    "measure": None,
    "currency_scope": None,
}

_MEASURE_ORDER = {"debt": 1, "overdue_debt": 2}
_CURRENCY_ORDER = {
    "rubles": 1,
    "foreign_currency_and_precious_metals": 2,
    "total": 3,
}
_MEASURE_SHEET_LABELS = {
    "debt": "Задолженность",
    "overdue_debt": "Просрочка",
}
_CURRENCY_SHEET_LABELS = {
    "rubles": "рубли",
    "foreign_currency_and_precious_metals": "инвалюта",
    "total": "итого",
}


class Cbr0105ADebtCorpPivotError(ValueError):
    """Структурированная ошибка подготовки pivot-таблиц для Strategy Box."""

    def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _raise(code: str, message: str, **details: object) -> None:
    raise Cbr0105ADebtCorpPivotError(code, message, details=details)


def _unique_values(series: pd.Series) -> list[object]:
    values: list[object] = []
    seen: set[tuple[str, object]] = set()
    for value in series.astype("object").tolist():
        key = ("na", "") if pd.isna(value) else ("value", value)
        if key in seen:
            continue
        seen.add(key)
        values.append(None if pd.isna(value) else value)
    return values


def _dimension_value_order(
    df_stream: pd.DataFrame,
    dimension: str,
    value: object,
) -> tuple[object, ...]:
    if value is None or pd.isna(value):
        return (1, "")
    if dimension == "report_date":
        return (0, str(value))
    if dimension == "measure":
        return (0, _MEASURE_ORDER.get(str(value), 10_000), str(value))
    if dimension == "currency_scope":
        return (0, _CURRENCY_ORDER.get(str(value), 10_000), str(value))
    order_column = _DIMENSION_ORDER_COLUMNS.get(dimension)
    if order_column and order_column in df_stream.columns:
        rows = df_stream.loc[df_stream[dimension].astype("object") == value, order_column]
        if not rows.empty:
            return (0, int(rows.min()), str(value))
    return (0, str(value))


def _ordered_dimension_values(df_stream: pd.DataFrame, dimension: str) -> list[object]:
    values = _unique_values(df_stream[dimension])
    return sorted(values, key=lambda value: _dimension_value_order(df_stream, dimension, value))


def _display_value(df_stream: pd.DataFrame, dimension: str, value: object) -> str:
    if value is None or pd.isna(value):
        return "NA"
    text = str(value)
    if dimension == "measure":
        return _MEASURE_SHEET_LABELS.get(text, text)
    if dimension == "currency_scope":
        return _CURRENCY_SHEET_LABELS.get(text, text)
    label_columns = {
        "region_code": "region_name",
        "industry_code": "industry_name_ru",
    }
    label_column = label_columns.get(dimension)
    if label_column and label_column in df_stream.columns:
        matched = df_stream.loc[df_stream[dimension].astype("object") == value, label_column]
        matched = matched.dropna()
        if not matched.empty:
            return str(matched.iloc[0])
    return text


def sanitize_excel_sheet_name(value: str, *, fallback: str = "Таблица") -> str:
    """Приводит имя листа к ограничениям Excel."""
    text = re.sub(r"[\[\]:*?/\\]", " ", str(value))
    text = re.sub(r"\s+", " ", text).strip(" '")
    return (text or fallback)[:31]


def _unique_sheet_name(candidate: str, used: set[str]) -> str:
    base = sanitize_excel_sheet_name(candidate)
    if base.lower() not in used:
        used.add(base.lower())
        return base
    counter = 2
    while True:
        suffix = f" ({counter})"
        current = f"{base[: 31 - len(suffix)]}{suffix}"
        if current.lower() not in used:
            used.add(current.lower())
            return current
        counter += 1


def _validate_request(df_stream: pd.DataFrame, request: Cbr0105ADebtCorpPivotRequest) -> None:
    if df_stream.empty:
        _raise("PIVOT_EMPTY_INPUT", "Невозможно построить pivot: поток пуст.")

    dimensions = set(CBR_0105A_DEBT_CORP_PIVOT_DIMENSIONS)
    roles = [request.row_dimension, request.column_dimension, *request.sheet_dimensions]
    unknown = [value for value in roles if value not in dimensions]
    if unknown:
        _raise(
            "PIVOT_INVALID_DIMENSION",
            f"Неизвестные измерения pivot: {unknown}",
            dimensions=unknown,
        )
    duplicates = sorted({value for value in roles if roles.count(value) > 1})
    if duplicates:
        _raise(
            "PIVOT_DUPLICATE_AXIS",
            f"Измерение назначено одновременно на несколько ролей: {duplicates}",
            dimensions=duplicates,
        )
    if not request.value_columns:
        _raise("PIVOT_EMPTY_VALUES", "Не выбрано ни одного числового поля.")
    if len(set(request.value_columns)) != len(request.value_columns):
        _raise(
            "PIVOT_DUPLICATE_VALUE_COLUMN",
            "Список числовых полей содержит дубли.",
            value_columns=request.value_columns,
        )
    if request.max_sheet_count < 1:
        _raise(
            "PIVOT_INVALID_MAX_SHEET_COUNT",
            "max_sheet_count должен быть положительным.",
            max_sheet_count=request.max_sheet_count,
        )

    required_columns = dimensions | set(_CONTEXT_DIMENSIONS) | set(request.value_columns)
    missing = sorted(required_columns - set(df_stream.columns))
    if missing:
        _raise(
            "PIVOT_MISSING_COLUMNS",
            f"В потоке отсутствуют обязательные поля: {missing}",
            columns=missing,
        )

    for column in request.value_columns:
        if column in _TECHNICAL_NUMERIC_COLUMNS or column in dimensions:
            _raise(
                "PIVOT_INVALID_VALUE_COLUMN",
                f"Поле {column!r} является измерением или техническим полем, а не значением.",
                column=column,
            )
        if not is_numeric_dtype(df_stream[column].dtype):
            _raise(
                "PIVOT_INVALID_VALUE_COLUMN",
                f"Поле {column!r} не является числовым.",
                column=column,
                dtype=str(df_stream[column].dtype),
            )


def _validate_stream_result(
    stream_result: Cbr0105ADebtCorpStreamResult | None,
    request: Cbr0105ADebtCorpPivotRequest,
) -> bool:
    if stream_result is None:
        return False
    errors = [issue for issue in stream_result.validation_issues if issue.severity == "error"]
    if errors:
        _raise(
            "PIVOT_INVALID_STREAM",
            "Pivot заблокирован: поток содержит ошибки валидации.",
            issue_codes=tuple(issue.code for issue in errors),
        )
    if request.require_complete_stream and stream_result.failures:
        _raise(
            "PIVOT_PARTIAL_STREAM",
            "Pivot требует полный поток, но часть источников не обработана.",
            failure_count=len(stream_result.failures),
        )
    return stream_result.is_partial


def _fixed_dimensions(
    df_stream: pd.DataFrame,
    request: Cbr0105ADebtCorpPivotRequest,
) -> tuple[tuple[str, object], ...]:
    used = {
        request.row_dimension,
        request.column_dimension,
        *request.sheet_dimensions,
    }
    fixed: list[tuple[str, object]] = []
    for dimension in (*CBR_0105A_DEBT_CORP_PIVOT_DIMENSIONS, *_CONTEXT_DIMENSIONS):
        if dimension in used:
            continue
        values = _unique_values(df_stream[dimension])
        if len(values) != 1:
            preview = tuple(values[:10])
            _raise(
                "PIVOT_RESIDUAL_DIMENSION_VARIATION",
                (
                    f"Измерение {dimension!r} содержит {len(values)} значений. "
                    "Отфильтруйте поток до одного значения либо назначьте измерение "
                    "строками, столбцами или измерением листов."
                ),
                dimension=dimension,
                unique_count=len(values),
                values=preview,
            )
        fixed.append((dimension, values[0]))
    return tuple(fixed)


def _sheet_groups(
    df_stream: pd.DataFrame,
    sheet_dimensions: tuple[str, ...],
) -> list[tuple[tuple[object, ...], pd.DataFrame]]:
    if not sheet_dimensions:
        return [((), df_stream)]

    grouper: str | list[str]
    grouper = sheet_dimensions[0] if len(sheet_dimensions) == 1 else list(sheet_dimensions)
    groups: list[tuple[tuple[object, ...], pd.DataFrame]] = []
    for raw_key, group in df_stream.groupby(
        grouper,
        observed=True,
        dropna=False,
        sort=False,
    ):
        key = raw_key if isinstance(raw_key, tuple) else (raw_key,)
        groups.append((key, group))
    return sorted(
        groups,
        key=lambda item: tuple(
            _dimension_value_order(df_stream, dimension, value)
            for dimension, value in zip(sheet_dimensions, item[0], strict=True)
        ),
    )


def _validate_descriptor_dependencies(
    df_stream: pd.DataFrame,
    row_dimension: str,
    descriptor_columns: Iterable[str],
) -> None:
    for column in descriptor_columns:
        if column == row_dimension or column not in df_stream.columns:
            continue
        counts = df_stream.groupby(row_dimension, observed=True, dropna=False)[column].nunique(
            dropna=False
        )
        invalid = counts[counts > 1]
        if not invalid.empty:
            _raise(
                "PIVOT_ROW_DESCRIPTOR_CONFLICT",
                f"Поле {column!r} неоднозначно для измерения {row_dimension!r}.",
                descriptor=column,
                row_dimension=row_dimension,
                conflicting_keys=tuple(str(value) for value in invalid.index[:10]),
            )


def _row_metadata(df_stream: pd.DataFrame, row_dimension: str, row_order: list[object]) -> pd.DataFrame:
    descriptors = tuple(
        column
        for column in _DIMENSION_DESCRIPTORS[row_dimension]
        if column in df_stream.columns
    )
    _validate_descriptor_dependencies(df_stream, row_dimension, descriptors)
    metadata = df_stream.loc[:, list(descriptors)].drop_duplicates(subset=[row_dimension])
    metadata = metadata.set_index(row_dimension).reindex(row_order).reset_index()
    return metadata


def _pivot_matrix(
    group: pd.DataFrame,
    *,
    row_dimension: str,
    column_dimension: str,
    value_columns: tuple[str, ...],
    row_order: list[object],
    column_order: list[object],
) -> pd.DataFrame:
    duplicate_mask = group.duplicated([row_dimension, column_dimension], keep=False)
    if duplicate_mask.any():
        sample = group.loc[duplicate_mask, [row_dimension, column_dimension]].iloc[0]
        sample_count = int(
            (
                (group[row_dimension].astype("object") == sample[row_dimension])
                & (group[column_dimension].astype("object") == sample[column_dimension])
            ).sum()
        )
        _raise(
            "PIVOT_DUPLICATE_CELL",
            "Несколько строк исходного потока попадают в одну ячейку pivot.",
            row_dimension=row_dimension,
            row_value=sample[row_dimension],
            column_dimension=column_dimension,
            column_value=sample[column_dimension],
            source_rows=sample_count,
        )

    values: str | list[str]
    values = value_columns[0] if len(value_columns) == 1 else list(value_columns)
    matrix = group.pivot(
        index=row_dimension,
        columns=column_dimension,
        values=values,
    )
    matrix = matrix.reindex(index=row_order)
    if len(value_columns) == 1:
        matrix = matrix.reindex(columns=column_order)
    else:
        matrix = matrix.swaplevel(0, 1, axis=1)
        expected = pd.MultiIndex.from_product(
            [column_order, value_columns],
            names=[column_dimension, "value_column"],
        )
        matrix = matrix.reindex(columns=expected)
    return matrix


def build_cbr_0105a_debt_corp_pivot_set(
    df_stream: pd.DataFrame,
    request: Cbr0105ADebtCorpPivotRequest,
    *,
    stream_result: Cbr0105ADebtCorpStreamResult | None = None,
) -> Cbr0105ADebtCorpPivotSetResult:
    """Строит набор таблиц из уже отфильтрованного потокового DataFrame.

    Операция не применяет предметные фильтры и не агрегирует конфликты. Любое
    остаточное смысловое измерение обязано иметь одно значение.
    """
    _validate_request(df_stream, request)
    is_partial = _validate_stream_result(stream_result, request)
    fixed_dimensions = _fixed_dimensions(df_stream, request)
    groups = _sheet_groups(df_stream, tuple(request.sheet_dimensions))
    if len(groups) > request.max_sheet_count:
        _raise(
            "PIVOT_TOO_MANY_SHEETS",
            (
                f"Разбиение создаёт {len(groups)} листов, что превышает предел "
                f"{request.max_sheet_count}."
            ),
            sheet_count=len(groups),
            max_sheet_count=request.max_sheet_count,
        )

    used_names: set[str] = set()
    tables: list[Cbr0105ADebtCorpPivotTable] = []
    for key_values, group in groups:
        row_order = _ordered_dimension_values(group, request.row_dimension)
        column_order = _ordered_dimension_values(group, request.column_dimension)
        matrix = _pivot_matrix(
            group,
            row_dimension=request.row_dimension,
            column_dimension=request.column_dimension,
            value_columns=request.value_columns,
            row_order=row_order,
            column_order=column_order,
        )
        metadata = _row_metadata(group, request.row_dimension, row_order)
        table = pd.concat(
            [metadata.reset_index(drop=True), matrix.reset_index(drop=True)],
            axis=1,
        )
        sheet_key = tuple(
            (dimension, None if pd.isna(value) else value)
            for dimension, value in zip(request.sheet_dimensions, key_values, strict=True)
        )
        sheet_parts = [
            _display_value(df_stream, dimension, value)
            for dimension, value in sheet_key
        ]
        suggested_name = _unique_sheet_name(" — ".join(sheet_parts) or "Таблица", used_names)
        tables.append(
            Cbr0105ADebtCorpPivotTable(
                sheet_key=sheet_key,
                suggested_sheet_name=suggested_name,
                row_dimension=request.row_dimension,
                column_dimension=request.column_dimension,
                value_columns=request.value_columns,
                df_table=table,
                rows=int(len(table)),
                data_columns=int(len(matrix.columns)),
                missing_values=int(matrix.isna().sum().sum()),
            )
        )

    return Cbr0105ADebtCorpPivotSetResult(
        tables=tuple(tables),
        row_dimension=request.row_dimension,
        column_dimension=request.column_dimension,
        value_columns=request.value_columns,
        sheet_dimensions=tuple(request.sheet_dimensions),
        fixed_dimensions=fixed_dimensions,
        source_rows=int(len(df_stream)),
        table_count=len(tables),
        is_partial=is_partial,
    )


__all__ = [
    "CBR_0105A_DEBT_CORP_PIVOT_DIMENSIONS",
    "Cbr0105ADebtCorpPivotError",
    "build_cbr_0105a_debt_corp_pivot_set",
    "sanitize_excel_sheet_name",
]
