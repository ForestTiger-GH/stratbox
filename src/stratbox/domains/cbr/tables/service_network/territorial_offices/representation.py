from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping

from stratbox.domains.cbr.tables.service_network.snapshots import detail_value
from stratbox.shared.data.releases import csv_rows

_COUNT_LABELS = frozenset({
    "головной офис", "головные офисы", "кредитные организации",
    "филиалы", "представительства", "дополнительные офисы",
    "мобильные офисы", "операционные кассы вне кассового узла",
    "кредитно-кассовые офисы", "операционные офисы",
    "передвижные пункты кассовых операций", "всего",
})


def count_label(heading: str) -> str | None:
    parts = [part.strip().casefold() for part in heading.split(" / ")]
    if any(re.search(r"\b(?:рубл|валют|процент|тыс|млн|млрд)\w*|%", part) for part in parts):
        return None
    for part in reversed(parts):
        part = re.sub(r"\s*\(ед\.?\)$|[1-9*]+$", "", part).strip()
        if part in _COUNT_LABELS:
            return part
    return None


def serialize(records):
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(records)
    return stream.getvalue().encode("utf-8")


def validate_csv(blob, *, minimum_rows: int = 30):
    from stratbox.domains.cbr.tables.service_network.territorial_offices.parser import CaptureError, MAX_ROW, MAX_WIDTH, clean, require

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
    require(len(rows) >= minimum_rows + 1, "CSV_TOO_FEW_ROWS")
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
        require(1 <= int(row[0]) <= MAX_ROW and int(row[0]) > previous, "CSV_ROW_ORDER")
        require(all(clean(value) == value for value in row), "CSV_CELL_NONCANONICAL")
        previous = int(row[0])
    require(serialize(rows) == blob, "CSV_NON_CANONICAL")
    return len(rows) - 1


def validate_source_details(details, data):
    """Validate the complete, explicitly supplied workbook evidence for CSV replay."""
    if not isinstance(details, Mapping) or not {"selection", "formula_lineage"} <= details.keys():
        raise ValueError("CSV_METADATA_INCOMPLETE")
    detail_value(details)
    selection, formulas = details["selection"], details["formula_lineage"]
    required = {"sheet", "header_rows", "first_row", "last_row", "territory_column", "column_order",
                "date_basis", "unresolved_fields", "scope"}
    if not isinstance(selection, Mapping) or not required <= selection.keys() or not isinstance(formulas, Mapping):
        raise ValueError("CSV_METADATA_INCOMPLETE")
    if (type(selection["sheet"]) is not str or not selection["sheet"]
            or selection["scope"] not in {"published_table", "selected_fragment"}
            or selection["date_basis"] not in {"printed", "release"}):
        raise ValueError("CSV_METADATA_INVALID")
    for name, maximum in (("first_row", 1_048_576), ("last_row", 1_048_576), ("territory_column", 16_384)):
        if type(selection[name]) is not int or not 1 <= selection[name] <= maximum:
            raise ValueError("CSV_METADATA_INVALID")
    for name in ("header_rows", "column_order", "unresolved_fields"):
        if not isinstance(selection[name], tuple) or len(set(selection[name])) != len(selection[name]):
            raise ValueError("CSV_METADATA_INVALID")
    if (any(type(row) is not int or not 1 <= row < selection["first_row"] for row in selection["header_rows"])
            or any(type(col) is not int or not 1 <= col <= 16_384 for col in selection["column_order"])):
        raise ValueError("CSV_METADATA_INVALID")
    rows = csv_rows(data)
    header = rows[0][2:]
    if (len(selection["column_order"]) != len(header)
            or selection["column_order"][0] != selection["territory_column"]
            or selection["first_row"] != int(rows[1][0]) or selection["last_row"] < int(rows[-1][0])
            or any(type(field) is not str or field not in header for field in selection["unresolved_fields"])):
        raise ValueError("CSV_METADATA_MISMATCH")
    source_rows = {row[0] for row in rows[1:]}
    headings = dict(zip(selection["column_order"], header))
    for row, columns in formulas.items():
        if row not in source_rows or not isinstance(columns, Mapping):
            raise ValueError("CSV_FORMULA_EVIDENCE_INVALID")
        for column, item in columns.items():
            if (type(column) is not str or not column.isascii() or not column.isdecimal()
                    or int(column) not in headings or not isinstance(item, Mapping)
                    or not set(item) <= {"formula", "attributes", "cache_missing", "error_value"}):
                raise ValueError("CSV_FORMULA_EVIDENCE_INVALID")
            if "formula" in item and type(item["formula"]) is not str:
                raise ValueError("CSV_FORMULA_EVIDENCE_INVALID")
            if "attributes" in item and (not isinstance(item["attributes"], Mapping)
                    or any(type(k) is not str or type(v) is not str for k, v in item["attributes"].items())):
                raise ValueError("CSV_FORMULA_EVIDENCE_INVALID")
            if any(flag in item and type(item[flag]) is not bool for flag in ("cache_missing", "error_value")):
                raise ValueError("CSV_FORMULA_EVIDENCE_INVALID")
            if (item.get("cache_missing") or item.get("error_value")) and headings[int(column)] not in selection["unresolved_fields"]:
                raise ValueError("CSV_FORMULA_EVIDENCE_INVALID")
    return selection
