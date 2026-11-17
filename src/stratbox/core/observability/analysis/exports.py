"""Schema-limited and formula-safe CSV projections of observed records."""
from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO
from collections.abc import Iterable, Mapping

def _safe_csv(value: object, spreadsheet_safe: bool) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, Decimal)) and type(value) is not bool:
        return str(value)
    result = str(value)
    if not spreadsheet_safe:
        return result
    # Leading whitespace and control characters must not obscure formulas.
    pos = 0
    while pos < len(result) and (result[pos].isspace() or ord(result[pos]) < 32
                                  or result[pos] in "\ufeff\u200b\u2060\u202e"):
        pos += 1
    stripped = result[pos:]
    if stripped and stripped[0] in "=+-@":
        return "'" + result
    return result


def export_projection_csv(rows: Iterable[Mapping[str, object]], *, columns: tuple[str, ...],
                          spreadsheet_safe: bool = True, max_rows: int = 100_000,
                          max_output_bytes: int = 16 * 1024 * 1024) -> bytes:
    if not columns or len(set(columns)) != len(columns) or any(type(x) is not str for x in columns):
        raise ValueError("A distinct CSV schema is required")
    output = StringIO(newline="")
    # CRLF ensures Python 3.10 also quotes embedded CR characters in CSV fields.
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="raise", lineterminator="\r\n")
    writer.writeheader()
    for count, row in enumerate(rows, 1):
        if count > max_rows:
            raise ValueError("journal.export_row_limit")
        if any(k not in columns for k in row):
            raise ValueError("Projection has fields outside the schema")
        writer.writerow({k: _safe_csv(row.get(k), spreadsheet_safe) for k in columns})
        if output.tell() > max_output_bytes:
            raise ValueError("journal.export_size_limit")
    return output.getvalue().encode("utf-8")
