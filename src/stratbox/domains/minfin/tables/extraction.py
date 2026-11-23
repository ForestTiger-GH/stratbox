"""Exact spreadsheet/CSV materialization and source-structure inspection."""
from __future__ import annotations
import csv
from datetime import date, datetime, time
from decimal import Decimal
from io import StringIO
from math import isfinite

from stratbox.core.formats.archives.members import ArchiveLimits, extract_members
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from .contracts import (Cell, CellChange, CompareRequest, ExtractRequest, Sheet,
                        SheetChange, TableComparison, TableExtract, ValidateRequest, Validation)

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


def _tables_workbook(data: bytes, kind: str, selected_sheets: tuple[str, ...], max_cells: int, invocation=None):
    from stratbox.core.formats.spreadsheets.extracts import extract_workbook
    book = extract_workbook(SourcePayload(data), series_id="minfin.material", issue_id="unidentified",
        budget=invocation.budget if invocation is not None else None,
        checkpoint=invocation.check_cancelled if invocation is not None else None)
    if book.format != kind:
        raise ValueError("minfin.workbook_type_mismatch")
    names = selected_sheets or tuple(sheet.name for sheet in book.sheets)
    if not names or len(set(names)) != len(names) or any(name not in {s.name for s in book.sheets} for name in names):
        raise ValueError("minfin.sheet_selection_invalid")
    selected = {sheet.name: sheet for sheet in book.sheets}
    count = 0
    result = []
    for name in names:
        sheet = selected[name]
        cells = []
        for item in sheet.cells:
            count += 1
            if count > max_cells:
                raise ValueError("minfin.cell_limit")
            text, cell_kind = _value(item.value)
            if item.kind == "e":
                cell_kind = "error"
            if item.formula is not None:
                cached = text if item.value is not None else None
                cells.append(Cell(name, item.row, item.column, "formula", "=" + item.formula,
                                  item.number_format, cached, item.raw_token, item.indent,
                                  item.formula_attributes, item.evidence_kind))
            else:
                cells.append(Cell(name, item.row, item.column, cell_kind, text, item.number_format,
                                  None, item.raw_token, item.indent, (), item.evidence_kind))
        result.append(Sheet(name, sheet.rows, sheet.columns, tuple(cells), sheet.merged_ranges))
    return tuple(result), book.qualifications


def extract_tables(request: ExtractRequest, invocation=None, *,
                   allowed_sources: frozenset[str], allowed_formats: frozenset[str]) -> TableExtract:
    """Exact source-cell extraction under an independently admitted source binding."""
    if not isinstance(request.payload, SourcePayload) or not 0 < request.payload.identity.size <= _LIMIT:
        raise ValueError("minfin.payload_invalid")
    if type(request.max_cells) is not int or not 1 <= request.max_cells <= 500_000:
        raise ValueError("minfin.cell_limit_invalid")
    if request.format not in allowed_formats or request.format not in {"xlsx", "xls", "xlsm", "csv", "zip"}:
        raise ValueError("minfin.format_unsupported")
    if not isinstance(allowed_sources, frozenset) or not allowed_sources:
        raise ValueError("minfin.binding_missing")
    if request.payload.source_id is not None and request.payload.source_id not in allowed_sources:
        raise ValueError("minfin.source_family_mismatch")
    if request.publication is not None and request.publication.series_id != request.payload.source_id:
        raise ValueError("minfin.publication_source_mismatch")
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
        tables, qualifications = _tables_workbook(data, ext, request.selected_sheets, request.max_cells, invocation)
    elif ext == "csv":
        if request.selected_sheets and request.selected_sheets != ("CSV",):
            raise ValueError("minfin.sheet_selection_invalid")
        tables = _tables_csv(data, request.max_cells, encoding=request.csv_encoding)
        qualifications = ("CSV source fields retain lexical text; numeric and date semantics are unapplied.",)
    else:
        raise ValueError("minfin.extract_unsupported_format")
    if invocation is not None:
        invocation.check_cancelled()
    return TableExtract(request.family_id, request.payload.source_id or request.family_id + ".attachments",
                        request.payload.identity, request.format, tables, member,
                        publication=request.publication, qualifications=qualifications)


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
        old_merges = a.merged_ranges if a is not None else ()
        new_merges = b.merged_ranges if b is not None else ()
        if previous != current or old_merges != new_merges:
            layout_changes.append(SheetChange(name, previous[0], previous[1], current[0], current[1], old_merges, new_merges))
    changes = []
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            changes.append(CellChange(*key, old.get(key), new.get(key)))
            if len(changes) > request.max_changes:
                raise ValueError("minfin.compare_limit_exceeded")
    return TableComparison(before.family_id, before.source_identity, after.source_identity, tuple(changes), tuple(layout_changes))


def validate_tables(request: ValidateRequest) -> Validation:
    value = request.extract
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
