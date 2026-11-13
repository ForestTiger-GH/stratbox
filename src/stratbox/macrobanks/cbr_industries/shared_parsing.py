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
    return rows, names


def _match_sheet_regions(expected, actual):
    """Align physical rows to the series geography after the first validated sheet."""
    lookup = {normalize_cbr_0105a_text(item.source_name): item for item in expected}
    names = tuple(normalize_cbr_0105a_text(name) for name in actual)
    if len(lookup) != len(expected) or len(set(names)) != len(names) or set(names) != lookup.keys():
        raise ValueError("Geographic rows differ between CBR industry sheets")
    return tuple(lookup[name] for name in names)


def _sheet_rows(rows, first, *, checkpoint):
    data = [first]
    for number, row in enumerate(rows):
        if checkpoint is not None and number % 128 == 0:
            checkpoint()
        data.append(tuple(row))
    return data


def _check_published_unit(title):
    unit_words = normalize_cbr_0105a_text(title)
    if re.search(r"\b(?:тыс|млрд)\s+(?:российских\s+)?руб\w*\b", unit_words) or "%" in str(title):
        raise ValueError("Published unit conflicts with the series definition")


