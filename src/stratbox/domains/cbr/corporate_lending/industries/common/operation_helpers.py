"""Shared family operation helpers with neutral execution/evidence semantics."""

from __future__ import annotations

from dataclasses import asdict, replace

from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution import OperationFailure
from stratbox.core.operations.tables import record_tables

_TABLE_LIMITS = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)


def _stream_metadata(request):
    if request.source is not None:
        return request.source
    return request.stream if hasattr(request.stream, "validation_issues") else None


def _select_industry(stream, code):
    if code is None:
        return stream
    if "industry_code" not in stream:
        raise OperationFailure("request.industry_unresolved")
    selected = stream.loc[stream["industry_code"].eq(code)]
    if selected.empty:
        raise OperationFailure("request.industry_unresolved")
    return selected


def _pivot_tables(result):
    return tuple((table.suggested_sheet_name, table.df_table) for table in result.tables)


def _pivot_metadata(result):
    return {
        "row_dimension": result.row_dimension, "column_dimension": result.column_dimension,
        "value_columns": result.value_columns, "sheet_dimensions": result.sheet_dimensions,
        "fixed_dimensions": result.fixed_dimensions, "source_rows": result.source_rows,
        "partial": result.is_partial, "sheets": [
            (table.sheet_key, table.rows, table.data_columns) for table in result.tables
        ],
    }


def _seal_pivots(invocation, result, request, *, industry_code=None):
    return replace(result, evidence=record_tables(invocation, _pivot_tables(result),
                                                   parameters={**asdict(request), "industry": industry_code},
                                                   metadata=_pivot_metadata(result)))
