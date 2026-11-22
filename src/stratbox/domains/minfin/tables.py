"""Bounded, source-faithful workbook and CSV extraction for Minfin publications.

No economic labels, periods, units or classification codes are inferred from
visual layout. A later explicit mapping is required for economic observations.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from math import isfinite

from stratbox.core.formats.archives.members import ArchiveLimits, extract_members
from stratbox.core.formats.spreadsheets.workbook_input import workbook_profile
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

from .models import (
    Cell, CellChange, CompareRequest, ExtractRequest, MapRequest, MappedObservations,
    MetricObservation, RenderRequest, Sheet, SheetChange, TableComparison, TableExtract, ValidateRequest, Validation,
)
from .registry import family

_LIMIT = 64 * 1024 * 1024


def _value(raw):
    if raw is None:
        return "", "blank"
    if type(raw) is bool:
        return "true" if raw else "false", "boolean"
    if type(raw) in (date, datetime, time):
        return raw.isoformat(), "date"
    if type(raw) is int:
        return str(raw), "number"
    if type(raw) is float and isfinite(raw):
        return repr(raw), "number"
    if isinstance(raw, Decimal) and raw.is_finite():
        return str(raw), "number"
    if isinstance(raw, str):
        if len(raw) > 32_767:
            raise ValueError("minfin.cell_text_limit")
        return raw, "text"
    raise ValueError("minfin.cell_value_unsupported")


def _tables_csv(data: bytes, max_cells: int, *, encoding: str) -> tuple[Sheet, ...]:
    if encoding not in {"utf-8", "utf-8-sig", "cp1251"}:
        raise ValueError("minfin.csv_encoding_invalid")
    try:
        text = data.decode(encoding, errors="strict")
    except UnicodeError:
        raise ValueError("minfin.csv_decoding_failed") from None
    if "\x00" in text or len(text) > 64 * 1024 * 1024:
        raise ValueError("minfin.csv_invalid")
    sep = ";" if text.count(";") > text.count(",") else ","
    reader = csv.reader(StringIO(text, newline=""), delimiter=sep, strict=True)
    cells = []
    largest = 0
    rows = 0
    try:
        for r, fields in enumerate(reader, 1):
            if r > 1_000_000 or len(fields) > 16_384 or len(cells) + len(fields) > max_cells:
                raise ValueError("minfin.cell_limit")
            rows = r
            largest = max(largest, len(fields))
            for c, value in enumerate(fields, 1):
                if len(value) > 32_767:
                    raise ValueError("minfin.cell_text_limit")
                cells.append(Cell("CSV", r, c, "text" if value else "blank", value))
    except csv.Error:
        raise ValueError("minfin.csv_invalid") from None
    return (Sheet("CSV", rows, largest, tuple(cells)),)


def _tables_xlsx(data: bytes, kind: str, selected_sheets: tuple[str, ...], max_cells: int) -> tuple[Sheet, ...]:
    require_extra("openpyxl", "excel")
    from openpyxl import load_workbook
    try:
        main = load_workbook(BytesIO(data), read_only=True, data_only=False, keep_links=False)
        values = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
        try:
            all_names = tuple(main.sheetnames)
            names = selected_sheets or all_names
            if len(set(names)) != len(names) or not names or any(name not in all_names for name in names):
                raise ValueError("minfin.sheet_selection_invalid")
            result: list[Sheet] = []
            count = 0
            for name in names:
                sh, cached = main[name], values[name]
                rows, cols = sh.max_row or 0, sh.max_column or 0
                if rows * cols > max_cells * 8 or rows > 1_000_000 or cols > 16_384:
                    raise ValueError("minfin.sheet_dense_limit")
                cells: list[Cell] = []
                for row, cached_row in zip(sh.iter_rows(), cached.iter_rows()):
                    for item, cv in zip(row, cached_row):
                        if item.value is None:
                            continue
                        count += 1
                        if count > max_cells:
                            raise ValueError("minfin.cell_limit")
                        if item.data_type == "f":
                            value, ckind = _value(item.value)
                            cache, _ = _value(cv.value)
                            cells.append(Cell(name, item.row, item.column, "formula", value,
                                              item.number_format or "", cache if cv.value is not None else None))
                        elif item.data_type == "e":
                            value, _ = _value(item.value)
                            cells.append(Cell(name, item.row, item.column, "error", value, item.number_format or ""))
                        else:
                            value, ckind = _value(item.value)
                            cells.append(Cell(name, item.row, item.column, ckind, value, item.number_format or ""))
                result.append(Sheet(name, rows, cols, tuple(cells)))
            return tuple(result)
        finally:
            main.close()
            values.close()
    except (OSError, KeyError, IndexError, EOFError, TypeError):
        raise ValueError("minfin.workbook_invalid") from None


def _tables_xls(data: bytes, selected_sheets: tuple[str, ...], max_cells: int) -> tuple[Sheet, ...]:
    require_extra("xlrd", "excel-legacy")
    import xlrd
    try:
        book = xlrd.open_workbook(file_contents=data, on_demand=True)
        try:
            all_names = tuple(book.sheet_names())
            names = selected_sheets or all_names
            if len(set(names)) != len(names) or not names or any(n not in all_names for n in names):
                raise ValueError("minfin.sheet_selection_invalid")
            results = []
            count = 0
            for name in names:
                sh = book.sheet_by_name(name)
                if sh.nrows * sh.ncols > max_cells * 8:
                    raise ValueError("minfin.sheet_dense_limit")
                cells = []
                for r in range(sh.nrows):
                    for c in range(sh.ncols):
                        val = sh.cell(r, c)
                        if val.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                            continue
                        count += 1
                        if count > max_cells:
                            raise ValueError("minfin.cell_limit")
                        if val.ctype == xlrd.XL_CELL_ERROR:
                            value, kind = str(val.value), "error"
                        elif val.ctype == xlrd.XL_CELL_BOOLEAN:
                            value, kind = _value(bool(val.value))
                        elif val.ctype == xlrd.XL_CELL_DATE:
                            value, kind = repr(val.value), "date_serial"  # retain epoch/basis without guessing timezone
                        else:
                            value, kind = _value(val.value)
                        cells.append(Cell(name, r + 1, c + 1, kind, value))
                results.append(Sheet(name, sh.nrows, sh.ncols, tuple(cells)))
            return tuple(results)
        finally:
            book.release_resources()
    except (OSError, xlrd.XLRDError):
        raise ValueError("minfin.workbook_invalid") from None


def extract_tables(request: ExtractRequest, invocation=None) -> TableExtract:
    spec = family(request.family_id)
    if not isinstance(request.payload, SourcePayload) or not 0 < request.payload.identity.size <= _LIMIT:
        raise ValueError("minfin.payload_invalid")
    if type(request.max_cells) is not int or not 1 <= request.max_cells <= 500_000:
        raise ValueError("minfin.cell_limit_invalid")
    if request.format not in spec.formats:
        raise ValueError("minfin.format_unsupported")
    permitted_ids = {spec.default_source_id, *(variant.source_id for variant in spec.variants)}
    if request.payload.source_id is not None and request.payload.source_id not in permitted_ids:
        raise ValueError("minfin.source_family_mismatch")
    data = request.payload.data
    member = request.member
    ext = request.format
    if invocation is not None:
        invocation.check_cancelled()
    if ext == "zip":
        if not member or not member.lower().endswith((".xlsx", ".xls", ".xlsm", ".csv")):
            raise ValueError("minfin.archive_member_required")
        limits = ArchiveLimits(500, 256 * 1024 * 1024, 64 * 1024 * 1024, _LIMIT)
        files = extract_members(data, select=lambda _: (member,), limits=limits,
                                checkpoint=invocation.check_cancelled if invocation is not None else None)
        data = files[member]
        ext = member.rsplit(".", 1)[-1].lower()
        if invocation is not None:
            invocation.use(UsedInputReceipt.for_payload(SourcePayload(data), "source_member",
                                                        container=request.payload.identity, member=member))
    elif member is not None:
        raise ValueError("minfin.member_not_applicable")
    if ext in {"xlsx", "xlsm", "xls"}:
        profile = workbook_profile(data, budget=invocation.budget if invocation is not None else None,
                                   cancelled=invocation.cancelled if invocation is not None else None)
        if profile.kind != ext:
            raise ValueError("minfin.workbook_type_mismatch")
        profile.check_materialization(invocation.budget if invocation is not None else None)
        tables = (_tables_xls(data, request.selected_sheets, request.max_cells) if ext == "xls"
                  else _tables_xlsx(data, ext, request.selected_sheets, request.max_cells))
    elif ext == "csv":
        if request.selected_sheets and request.selected_sheets != ("CSV",):
            raise ValueError("minfin.sheet_selection_invalid")
        tables = _tables_csv(data, request.max_cells, encoding=request.csv_encoding)
    else:
        raise ValueError("minfin.extract_unsupported_format")
    if invocation is not None:
        invocation.check_cancelled()
    return TableExtract(request.family_id, request.payload.source_id or spec.default_source_id,
                        request.payload.identity, request.format, tables, member)


def compare_tables(request: CompareRequest) -> TableComparison:
    before, after = request.before, request.after
    if (before.family_id != after.family_id or before.source_id != after.source_id or
        before.member != after.member or before.format != after.format):
        raise ValueError("minfin.compare_incompatible_sources")
    if type(request.max_changes) is not int or not 1 <= request.max_changes <= 500_000:
        raise ValueError("minfin.compare_limit_invalid")
    old = {(c.sheet, c.row, c.column): c for sh in before.sheets for c in sh.cells}
    new = {(c.sheet, c.row, c.column): c for sh in after.sheets for c in sh.cells}
    old_layout = {sheet.name: sheet for sheet in before.sheets}
    new_layout = {sheet.name: sheet for sheet in after.sheets}
    layout_changes = []
    for name in sorted(set(old_layout) | set(new_layout)):
        a, b = old_layout.get(name), new_layout.get(name)
        previous = (a.rows, a.columns) if a is not None else (None, None)
        current = (b.rows, b.columns) if b is not None else (None, None)
        if previous != current:
            layout_changes.append(SheetChange(name, previous[0], previous[1], current[0], current[1]))
    changes = []
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            changes.append(CellChange(*key, old.get(key), new.get(key)))
            if len(changes) > request.max_changes:
                raise ValueError("minfin.compare_limit_exceeded")
    return TableComparison(before.family_id, before.source_identity, after.source_identity, tuple(changes), tuple(layout_changes))


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


def map_metrics(request: MapRequest) -> MappedObservations:
    if not request.bindings:
        raise ValueError("minfin.mapping_empty")
    indexed = {(c.sheet, c.row, c.column): c for sh in request.extract.sheets for c in sh.cells}
    seen = set()
    observations = []
    for binding in request.bindings:
        key = (binding.sheet, binding.row, binding.column)
        identity = (binding.metric_id, binding.period_id, binding.geography_id, binding.value_basis)
        if identity in seen:
            raise ValueError("minfin.mapping_duplicate")
        seen.add(identity)
        if not all((binding.metric_id, binding.period_id, binding.geography_id, binding.unit, binding.value_basis)):
            raise ValueError("minfin.mapping_incomplete")
        cell = indexed.get(key)
        if cell is None or cell.kind not in {"number", "formula"}:
            raise ValueError("minfin.mapping_value_unavailable")
        value = cell.cached if cell.kind == "formula" else cell.value
        try:
            parsed = Decimal(value)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("minfin.mapping_value_invalid") from None
        if not parsed.is_finite():
            raise ValueError("minfin.mapping_value_invalid")
        observations.append(MetricObservation(binding.metric_id, binding.period_id,
                          binding.geography_id, str(parsed), binding.value_basis, binding.unit,
                          *key))
    return MappedObservations(request.extract.family_id, request.extract.source_identity, tuple(observations))


__all__ = ("extract_tables", "compare_tables", "render_csv", "map_metrics")


def validate_tables(request: ValidateRequest) -> Validation:
    value = request.extract
    family(value.family_id)
    coordinates = [(c.sheet, c.row, c.column) for sh in value.sheets for c in sh.cells]
    if len(set(coordinates)) != len(coordinates):
        raise ValueError("minfin.extract_duplicate_cell")
    for sh in value.sheets:
        if not sh.name or sh.rows < 0 or sh.columns < 0 or any(
            c.sheet != sh.name or not (1 <= c.row <= sh.rows and 1 <= c.column <= sh.columns)
            for c in sh.cells
        ):
            raise ValueError("minfin.extract_invalid_geometry")
    return Validation(value.family_id, len(coordinates), len(value.sheets),
                      sum(c.kind == "formula" and c.cached is None for sh in value.sheets for c in sh.cells),
                      tuple(sh.name for sh in value.sheets if not sh.cells))


__all__ = ("extract_tables", "compare_tables", "render_csv", "map_metrics", "validate_tables")


def serialize_tables(request) -> Representation:
    """Round-trip representation for a domain extract, independent of physical storage.

    The source digest describes the acquired original, not these JSON bytes.
    Sheet extents and cell kinds survive a round trip, including empty sheets.
    """
    import json

    value = request.extract
    family(value.family_id)
    document = {
        "schema": "minfin.source_cells.v1",
        "family_id": value.family_id,
        "source_id": value.source_id,
        "source_sha256": value.source_identity.sha256,
        "source_size": value.source_identity.size,
        "format": value.format,
        "member": value.member,
        "coverage": value.coverage,
        "sheets": [
            {
                "name": sheet.name, "rows": sheet.rows, "columns": sheet.columns,
                "cells": [
                    [cell.row, cell.column, cell.kind, cell.value, cell.number_format, cell.cached]
                    for cell in sheet.cells
                ],
            }
            for sheet in value.sheets
        ],
    }
    data = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if not 0 < len(data) <= 64 * 1024 * 1024:
        raise ValueError("minfin.representation_size_invalid")
    return Representation("minfin.source_cells", 1, "application/json", data, encoding="utf-8")


def read_serialized_tables(request) -> TableExtract:
    """Load and validate retained representation; no source data is silently reinterpreted."""
    import json
    import re

    representation = request.representation
    if (not isinstance(representation, Representation) or
            (representation.profile_id, representation.version, representation.media_type, representation.encoding)
            != ("minfin.source_cells", 1, "application/json", "utf-8") or
            not 0 < len(representation.data) <= 64 * 1024 * 1024):
        raise ValueError("minfin.representation_invalid")
    try:
        document = json.loads(representation.data.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError("minfin.representation_invalid") from None
    if not isinstance(document, dict) or set(document) != {
        "schema", "family_id", "source_id", "source_sha256", "source_size",
        "format", "member", "coverage", "sheets",
    } or document["schema"] != "minfin.source_cells.v1":
        raise ValueError("minfin.representation_invalid")
    fam = family(document["family_id"])
    if (not isinstance(document["source_id"], str) or
        document["source_id"] not in {fam.default_source_id, *(v.source_id for v in fam.variants)} or
        document["format"] not in fam.formats or
        not isinstance(document["coverage"], str) or
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
        if not isinstance(entry, dict) or set(entry) != {"name", "rows", "columns", "cells"}:
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
            if not isinstance(raw, list) or len(raw) != 6:
                raise ValueError("minfin.representation_invalid")
            row, col, kind, val, fmt, cached = raw
            if (type(row) is not int or type(col) is not int or not 1 <= row <= rows or
                    not 1 <= col <= cols or (row, col) in seen or
                    not isinstance(kind, str) or kind not in {
                    "blank", "boolean", "date", "date_serial", "number", "text", "formula", "error"
                    } or not isinstance(val, str) or len(val) > 32_767 or
                    not isinstance(fmt, str) or len(fmt) > 512 or
                    not (cached is None or isinstance(cached, str) and len(cached) <= 32_767)):
                raise ValueError("minfin.representation_invalid")
            seen.add((row, col))
            cells.append(Cell(name, row, col, kind, val, fmt, cached))
            total += 1
            if total > 500_000:
                raise ValueError("minfin.cell_limit")
        sheets.append(Sheet(name, rows, cols, tuple(cells)))
    member = document["member"]
    if member is not None and (not isinstance(member, str) or len(member) > 512 or ".." in member):
        raise ValueError("minfin.representation_invalid")
    return TableExtract(document["family_id"], document["source_id"],
                        ByteIdentity(document["source_sha256"], document["source_size"]),
                        document["format"], tuple(sheets), member, document["coverage"])


__all__ = (
    "extract_tables", "compare_tables", "render_csv", "map_metrics", "validate_tables",
    "serialize_tables", "read_serialized_tables",
)