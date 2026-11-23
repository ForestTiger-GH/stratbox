"""Extract publication-local rows, decoded cells and numeric observations.

The original XLSX remains the byte-faithful carrier. Cell tokens describe the
openpyxl decoded scalar (not the original XML spelling). Unknown headers,
non-numeric tokens and formulas remain explicit cells rather than disappearing.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re

import pandas as pd
from openpyxl import load_workbook

from stratbox.shared.identity import ByteIdentity
from .columns import HEADER_SUBJECT_REQUIRED_TOKENS, is_subject_header_cell, probe_indicator_columns, resolve_indicator_spec_by_header
from .contracts import ParsedEscrowFile
from .rows import parse_escrow_rows

_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_MARKERS = frozenset(("-", "–", "—", "...", "…", "н/д", "н.д.", "n/a"))
_HEADER_MIN_PROBE_RECOGNIZED = 5
ROW_COLUMNS = ("display_order", "row_kind", "Регион", "federal_district_name", "region_number")
LONG_COLUMNS = ("Регион", "Показатель", "Значение", "Дата", "row_kind", "display_order", "federal_district_name", "region_number", "indicator_code", "value_kind", "source_name")
CELL_COLUMNS = ("source_row", "source_column", "source_header", "indicator_code", "raw_token", "raw_kind", "status", "value", "row_kind", "region", "display_order")


def extract_date_from_filename(name: str) -> str | None:
    match = _DATE_RE.search(str(name))
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else None


def clean_indicator_name(value: object) -> str:
    return resolve_indicator_spec_by_header(value).canonical_name


def decode_cell(value: object) -> tuple[str | None, str, str, Decimal | None]:
    """Keep blank, marker, unparsed and numeric values semantically distinct."""
    if value is None:
        return None, "blank", "blank", None
    if isinstance(value, bool):
        return str(value), "boolean", "unparsed", None
    if isinstance(value, (date, datetime)):
        return value.isoformat(), "datetime", "unparsed", None
    token = str(value)
    kind = "number" if isinstance(value, (int, float, Decimal)) else "text"
    if kind == "text" and token.startswith("="):
        return token, "formula", "formula_unresolved", None
    text = token.replace("\u00a0", " ").replace("\u202f", " ").strip()
    if not text:
        return token, kind, "blank", None
    if text.casefold() in _MARKERS:
        return token, kind, "marker", None
    normalized = text.replace(" ", "").replace(",", ".")
    if _NUMBER.fullmatch(normalized):
        try:
            number = Decimal(normalized)
        except InvalidOperation:
            pass
        else:
            if number.is_finite():
                return token, kind, "numeric", number
    return token, kind, "unparsed", None


def _coerce_numeric_value(value: object) -> Decimal | None:
    return decode_cell(value)[3]


def _find_header_row(sheet_df: pd.DataFrame) -> tuple[int, list[object]]:
    for row_index in range(min(len(sheet_df), 25)):
        row_values = sheet_df.iloc[row_index].tolist()
        if len(row_values) < 3 or not is_subject_header_cell(row_values[1]):
            continue
        resolved, _ = probe_indicator_columns(row_values, allow_unknown=True)
        if len(resolved) >= _HEADER_MIN_PROBE_RECOGNIZED:
            return row_index, row_values
    raise ValueError(f"Escrow header is unresolved: {HEADER_SUBJECT_REQUIRED_TOKENS}")


def _select_sheet_with_header(file_bytes: bytes) -> tuple[str, pd.DataFrame, int, list[object]]:
    workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=False)
    try:
        for name in sorted(workbook.sheetnames, key=lambda value: (0 if "регион" in value.lower() else 1, value.lower())):
            rows = list(workbook[name].iter_rows(values_only=True))
            frame = pd.DataFrame(rows, dtype=object)
            try:
                header_row, values = _find_header_row(frame)
            except ValueError:
                continue
            return name, frame, header_row, values
    finally:
        workbook.close()
    raise ValueError("Escrow sheet with a supported header is not found")


def _build_rows_frame(rows) -> pd.DataFrame:
    return pd.DataFrame([
        (row.display_order, row.row_kind, row.entity_name, row.federal_district_name, row.region_number)
        for row in rows
    ], columns=ROW_COLUMNS, dtype=object)


def parse_escrow_excel_bytes(file_bytes: bytes, *, source_name: str, as_of: str | None = None) -> ParsedEscrowFile:
    file_date = as_of if as_of is not None else extract_date_from_filename(source_name)
    if file_date is None:
        raise ValueError("Escrow observation date is required")
    date.fromisoformat(file_date)
    sheet_name, sheet_df, header_row, headers = _select_sheet_with_header(file_bytes)
    columns, unknown = probe_indicator_columns(headers, allow_unknown=True)
    data = sheet_df.iloc[header_row + 1:].reset_index(drop=True)
    rows = parse_escrow_rows(data)
    resolved = {column.source_index: column for column in columns}
    source_columns = sorted(set(resolved) | {index for index, _ in unknown})
    cells, records = [], []
    for row in rows:
        for column_index in source_columns:
            column = resolved.get(column_index)
            raw, kind, status, number = decode_cell(data.iat[row.source_row_index, column_index])
            cells.append((header_row + row.source_row_index + 2, column_index + 1,
                          str(headers[column_index]), column.spec.code if column else None,
                          raw, kind, status, number, row.row_kind, row.entity_name, row.display_order))
            if column is not None and number is not None:
                records.append((row.entity_name, column.spec.canonical_name, number, file_date,
                                row.row_kind, row.display_order, row.federal_district_name, row.region_number,
                                column.spec.code, column.spec.value_kind, source_name))
    return ParsedEscrowFile(
        source_name, file_date, sheet_name, header_row, columns, rows,
        _build_rows_frame(rows), pd.DataFrame(records, columns=LONG_COLUMNS, dtype=object),
        unmapped_headers=tuple(label for _, label in unknown),
        df_cells=pd.DataFrame(cells, columns=CELL_COLUMNS, dtype=object),
        original_identity=ByteIdentity.of(file_bytes),
    )


__all__ = ["ParsedEscrowFile", "clean_indicator_name", "extract_date_from_filename", "parse_escrow_excel_bytes"]
