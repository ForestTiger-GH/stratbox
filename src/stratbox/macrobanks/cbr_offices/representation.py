from __future__ import annotations

import csv
import io

from .parser import (
    CSV_PREFIX,
    MAX_CSV,
    MAX_ROWS,
    SOURCE_IDENTITIES,
    clean_text,
    fail,
    header_identity,
)


def serialize_csv(records: list[tuple[str, ...]]) -> bytes:
    """Serialize a complete wide table: first record is its source-faithful header."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8", "strict")


def validate_csv_bytes(data: bytes) -> tuple[int, int]:
    """Validate one row per source observation; never reinterpret blank or zero."""
    if not data or len(data) > MAX_CSV or data.startswith(b"\xef\xbb\xbf"):
        fail("CSV_SIZE_OR_BOM")
    try:
        content = data.decode("utf-8", "strict")
        rows = list(csv.reader(io.StringIO(content, newline=""), strict=True))
    except (UnicodeError, csv.Error):
        fail("CSV_INVALID_ENCODING")
    if len(rows) < 2:
        fail("CSV_HEADER_OR_EMPTY")
    header = rows[0]
    width = len(header)
    if (
        not 6 <= width <= 42
        or tuple(header[:2]) != CSV_PREFIX
        or tuple(header_identity(value) for value in header[2:5]) != SOURCE_IDENTITIES
        or any(not name or clean_text(name) != name for name in header)
        or len({header_identity(name) for name in header}) != width
    ):
        fail("CSV_HEADER_INVALID")
    previous_row = 0
    for record in rows[1:]:
        if len(record) != width:
            fail("CSV_COLUMN_COUNT")
        if any(clean_text(value) != value for value in record):
            fail("CSV_CELL_NOT_CANONICAL")
        source = record[0]
        if not source.isascii() or not source.isdecimal():
            fail("CSV_INDEX_INVALID")
        source_row = int(source)
        if not 1 <= source_row <= MAX_ROWS or source_row <= previous_row:
            fail("CSV_ORDER_INVALID")
        if any(not record[index] for index in (2, 3, 4)):
            fail("CSV_IDENTIFIERS_INVALID")
        previous_row = source_row
    if serialize_csv([tuple(record) for record in rows]) != data:
        fail("CSV_NON_CANONICAL")
    count = len(rows) - 1
    return count, count * (width - len(CSV_PREFIX) - 3)
