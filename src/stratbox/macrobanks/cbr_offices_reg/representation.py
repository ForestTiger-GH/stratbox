from __future__ import annotations

import csv
import io


def serialize(records):
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(records)
    return stream.getvalue().encode("utf-8")


def validate_csv(blob):
    from .parser import CaptureError, MAX_WIDTH, clean, require

    require(
        blob and not blob.startswith(b"\xef\xbb\xbf") and len(blob) < 8_000_000,
        "CSV_BAD_SIZE",
    )
    try:
        rows = list(
            csv.reader(io.StringIO(blob.decode("utf-8"), newline=""), strict=True)
        )
    except (UnicodeError, csv.Error):
        raise CaptureError("CSV_READ_FAILED") from None
    require(len(rows) >= 31, "CSV_TOO_FEW_ROWS")
    width = len(rows[0])
    require(
        6 <= width <= MAX_WIDTH + 2
        and rows[0][:2] == ["source_row", "section_label"]
        and all(rows[0][2:])
        and len(set(rows[0])) == width,
        "CSV_HEADER_INVALID",
    )
    previous = 0
    for row in rows[1:]:
        require(
            len(row) == width and row[0].isascii() and row[0].isdecimal(),
            "CSV_ROW_INVALID",
        )
        require(1 <= int(row[0]) <= 30000 and int(row[0]) > previous, "CSV_ROW_ORDER")
        require(all(clean(value) == value for value in row), "CSV_CELL_NONCANONICAL")
        previous = int(row[0])
    require(serialize(rows) == blob, "CSV_NON_CANONICAL")
    return len(rows) - 1
