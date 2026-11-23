"""Deterministic source-cell and clean-flake representations."""
from __future__ import annotations
import csv
from io import StringIO
from stratbox.shared.data.representation import Representation
from .contracts import (Cell, RenderRequest, RenderFlakeRequest, Sheet, TableExtract)
from ..publications.context import context_document, context_from_document

def render_csv(request: RenderRequest) -> Representation:
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("family_id", "source_id", "source_sha256", "member", "sheet", "row", "column",
                     "kind", "value", "number_format", "cached"))
    item = request.extract
    for sh in item.sheets:
        for c in sh.cells:
            writer.writerow((item.family_id, item.source_id, item.source_identity.sha256,
                             item.member or "", sh.name, c.row, c.column, c.kind,
                             c.value, c.number_format, c.cached if c.cached is not None else ""))
    return Representation("minfin.source_cells", 1, "text/csv", stream.getvalue().encode("utf-8"), encoding="utf-8")


def serialize_tables(request) -> Representation:
    """Round-trip representation for a domain extract, independent of physical storage.

    The source digest describes the acquired original, not these JSON bytes.
    Sheet extents and cell kinds survive a round trip, including empty sheets.
    """
    import json

    value = request.extract
    from .extraction import validate_tables
    from .contracts import ValidateRequest
    validate_tables(ValidateRequest(value))
    if (not isinstance(value.qualifications, tuple) or any(type(x) is not str or not x for x in value.qualifications)
            or value.publication is not None and value.publication.series_id != value.source_id):
        raise ValueError("minfin.representation_invalid")
    document = {
        "schema": "minfin.source_cells.v2",
        "family_id": value.family_id,
        "source_id": value.source_id,
        "source_sha256": value.source_identity.sha256,
        "source_size": value.source_identity.size,
        "format": value.format,
        "member": value.member,
        "coverage": value.coverage,
        "publication": context_document(value.publication),
        "qualifications": value.qualifications,
        "sheets": [
            {
                "name": sheet.name, "rows": sheet.rows, "columns": sheet.columns,
                "merged_ranges": list(sheet.merged_ranges),
                "cells": [
                    [cell.row, cell.column, cell.kind, cell.value, cell.number_format, cell.cached,
                     cell.raw_token, cell.indent, cell.formula_attributes, cell.evidence_kind]
                    for cell in sheet.cells
                ],
            }
            for sheet in value.sheets
        ],
    }
    data = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if not 0 < len(data) <= 64 * 1024 * 1024:
        raise ValueError("minfin.representation_size_invalid")
    return Representation("minfin.source_cells", 2, "application/json", data, encoding="utf-8")


def read_serialized_tables(request) -> TableExtract:
    """Load and validate retained representation; no source data is silently reinterpreted."""
    import json
    import re

    representation = request.representation
    if (not isinstance(representation, Representation) or
            (representation.profile_id, representation.version, representation.media_type, representation.encoding)
            != ("minfin.source_cells", 2, "application/json", "utf-8") or
            not 0 < len(representation.data) <= 64 * 1024 * 1024):
        raise ValueError("minfin.representation_invalid")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("minfin.representation_invalid")
            result[key] = value
        return result

    try:
        document = json.loads(representation.data.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError("minfin.representation_invalid") from None
    if not isinstance(document, dict) or set(document) != {
        "schema", "family_id", "source_id", "source_sha256", "source_size",
        "format", "member", "coverage", "sheets", "publication", "qualifications",
    } or document["schema"] != "minfin.source_cells.v2":
        raise ValueError("minfin.representation_invalid")
    if (not isinstance(document["family_id"], str) or not document["family_id"].startswith("minfin.") or
        not isinstance(document["source_id"], str) or not document["source_id"].startswith(document["family_id"] + ".") or
        document["format"] not in {"xlsx", "xls", "xlsm", "csv", "zip"} or
        not isinstance(document["coverage"], str) or
        not isinstance(document["qualifications"], list) or
        any(type(item) is not str or not item for item in document["qualifications"]) or
        not isinstance(document["sheets"], list) or
        not 1 <= len(document["sheets"]) <= 500 or
        not isinstance(document["source_size"], int) or
        not 0 < document["source_size"] <= 64 * 1024 * 1024 or
        not isinstance(document["source_sha256"], str) or
        not re.fullmatch(r"[0-9a-f]{64}", document["source_sha256"])):
        raise ValueError("minfin.representation_invalid")
    from stratbox.shared.identity import ByteIdentity
    sheets = []
    total = 0
    names = set()
    for entry in document["sheets"]:
        if not isinstance(entry, dict) or set(entry) != {"name", "rows", "columns", "cells", "merged_ranges"}:
            raise ValueError("minfin.representation_invalid")
        name, rows, cols = entry["name"], entry["rows"], entry["columns"]
        if (not isinstance(name, str) or not name or len(name) > 255 or name in names or
                type(rows) is not int or type(cols) is not int or
                not 0 <= rows <= 1_048_576 or not 0 <= cols <= 16_384 or
                not isinstance(entry["cells"], list)):
            raise ValueError("minfin.representation_invalid")
        names.add(name)
        cells = []
        seen = set()
        for raw in entry["cells"]:
            if not isinstance(raw, list) or len(raw) != 10:
                raise ValueError("minfin.representation_invalid")
            row, col, kind, val, fmt, cached, token, indent, attributes, evidence_kind = raw
            if (type(row) is not int or type(col) is not int or not 1 <= row <= rows or
                    not 1 <= col <= cols or (row, col) in seen or
                    not isinstance(kind, str) or kind not in {
                    "blank", "boolean", "date", "date_serial", "number", "text", "formula", "error"
                    } or not isinstance(val, str) or len(val) > 32_767 or
                    not isinstance(fmt, str) or len(fmt) > 512 or
                    not (cached is None or isinstance(cached, str) and len(cached) <= 32_767)):
                raise ValueError("minfin.representation_invalid")
            if (evidence_kind not in {"source_lexeme", "decoded_binary"} or token is not None and not isinstance(token, str) or type(indent) is not int or
                    not 0 <= indent <= 250 or not isinstance(attributes, list) or
                    any(not isinstance(pair, list) or len(pair) != 2 or
                        any(type(x) is not str for x in pair) for pair in attributes)):
                raise ValueError("minfin.representation_invalid")
            seen.add((row, col))
            cells.append(Cell(name, row, col, kind, val, fmt, cached, token, indent,
                              tuple(tuple(pair) for pair in attributes), evidence_kind))
            total += 1
            if total > 500_000:
                raise ValueError("minfin.cell_limit")
        merges = entry["merged_ranges"]
        if not isinstance(merges, list) or any(not isinstance(x, str) or not re.fullmatch(r"[A-Z]+[1-9][0-9]*:[A-Z]+[1-9][0-9]*", x) for x in merges):
            raise ValueError("minfin.representation_invalid")
        sheets.append(Sheet(name, rows, cols, tuple(cells), tuple(merges)))
    member = document["member"]
    if member is not None and (not isinstance(member, str) or len(member) > 512 or ".." in member):
        raise ValueError("minfin.representation_invalid")
    publication = context_from_document(document["publication"])
    if publication is not None and publication.series_id != document["source_id"]:
        raise ValueError("minfin.publication_source_mismatch")
    return TableExtract(document["family_id"], document["source_id"],
                        ByteIdentity(document["source_sha256"], document["source_size"]),
                        document["format"], tuple(sheets), member, document["coverage"],
                        publication, tuple(document["qualifications"]))


def render_flake_csv(request: RenderFlakeRequest) -> Representation:
    value = request.flake
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("code", "indicator", *(col.period_id for col in value.columns)))
    for row in value.rows:
        if len(row.values) != len(value.columns):
            raise ValueError("minfin.flake.invalid_row_width")
        writer.writerow((row.code, row.indicator, *(v if v is not None else "" for v in row.values)))
    data = buffer.getvalue().encode("utf-8-sig")
    return Representation("minfin.flake", 1, "text/csv", data, encoding="utf-8-sig")
