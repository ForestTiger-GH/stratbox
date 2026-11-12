"""Shared strict physical cell, industry-header and geographic-row parsing for SORS XLSX."""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation

from stratbox.macrobanks.cbr_industries.schema import normalize_cbr_0105a_text

def _coerce_numeric_value(value: object, *, coordinate: str, sheet_name: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(
            f"Boolean value in CBR industry data cell: sheet={sheet_name!r}, cell={coordinate}"
        )
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                f"Non-finite value in CBR industry: sheet={sheet_name!r}, cell={coordinate}"
            )
        return int(value) if value.is_integer() else value

    text = str(value).replace("\xa0", " ").strip()
    if not text:
        return None
    normalized = text.replace(" ", "").replace(",", ".")
    try:
        number = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(
            "Non-numeric value in CBR industry data cell: "
            f"sheet={sheet_name!r}, cell={coordinate}, value={value!r}"
        ) from exc
    if not number.is_finite():
        raise ValueError(
            f"Non-finite value in CBR industry: sheet={sheet_name!r}, cell={coordinate}"
        )
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def _non_empty_industry_headers(
    sheet_rows: list[tuple[object, ...]],
    *,
    sheet_name: str,
) -> list[tuple[int, object]]:
    if len(sheet_rows) < 3:
        raise ValueError(f"CBR industry sheet has fewer than 3 rows: {sheet_name!r}")
    headers: list[tuple[int, object]] = []
    for column, value in enumerate(sheet_rows[2][1:], start=2):
        if normalize_cbr_0105a_text(value):
            headers.append((column, value))
    expected_columns = list(range(2, 2 + len(headers)))
    actual_columns = [column for column, _ in headers]
    if actual_columns != expected_columns:
        raise ValueError(
            "CBR industry industry columns must be contiguous from column B: "
            f"sheet={sheet_name!r}, columns={actual_columns}"
        )
    return headers


def _region_names(
    sheet_rows: list[tuple[object, ...]],
    *,
    sheet_name: str,
) -> tuple[list[int], list[str]]:
    rows: list[int] = []
    names: list[str] = []
    for row, values in enumerate(sheet_rows[3:], start=4):
        value = values[0] if values else None
        if value is None or not str(value).replace("\xa0", " ").strip():
            continue
        rows.append(row)
        names.append(re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip())
    if not rows:
        raise ValueError(f"CBR industry contains no regions: sheet={sheet_name!r}")
    if rows != list(range(rows[0], rows[0] + len(rows))):
        raise ValueError(
            "CBR industry geographic rows are not contiguous: "
            f"sheet={sheet_name!r}, rows={rows[:5]}...{rows[-5:]}"
        )
    return rows, names


def _validate_sheet_region_names(
    expected: list[str] | None,
    actual: list[str],
    *,
    sheet_name: str,
) -> list[str]:
    if expected is None:
        return actual
    normalized_expected = [normalize_cbr_0105a_text(value) for value in expected]
    normalized_actual = [normalize_cbr_0105a_text(value) for value in actual]
    if normalized_expected != normalized_actual:
        raise ValueError(
            "Geographic rows differ between CBR industry sheets: "
            f"sheet={sheet_name!r}"
        )
    return expected


