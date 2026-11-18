from __future__ import annotations

import csv
import io
import re

from .parser import COLUMNS, LIMIT_JSON, FnsError, counter, require


def write_csv(rows):
    with io.StringIO(newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(rows[k] for k in sorted(rows))
        return output.getvalue().encode("utf-8")


def read_csv(blob):
    require(0 < len(blob) <= LIMIT_JSON, "CSV_SIZE_INVALID")
    try:
        text = blob.decode("utf-8")
        with io.StringIO(text, newline="") as fp:
            reader = csv.reader(fp, strict=True)
            require(tuple(next(reader)) == COLUMNS, "CSV_HEADER_INVALID")
            rows = {}
            for row in reader:
                require(len(row) == len(COLUMNS), "CSV_WIDTH_INVALID")
                code, label, *vals = row
                require(
                    re.fullmatch(r"[0-9]{1,3}", code) is not None
                    and code not in rows
                    and bool(label)
                    and not any(ord(ch) < 32 for ch in label),
                    "CSV_REGION_INVALID",
                )
                for val in vals:
                    counter(val)
                require(
                    int(vals[0]) == sum(map(int, vals[1:])), "CSV_TOTAL_INCONSISTENT"
                )
                rows[code] = tuple(row)
            require(80 <= len(rows) <= 120, "CSV_ROWS_INVALID")
            require(write_csv(rows) == blob, "CSV_NON_CANONICAL")
            return rows
    except (UnicodeError, csv.Error, StopIteration):
        raise FnsError("CSV_INVALID") from None
