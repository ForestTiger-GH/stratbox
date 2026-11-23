"""Publisher-neutral workbook extraction with explicit decoder evidence levels."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO

from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from .cells import read_workbook_cells
from .workbook_input import WorkbookError, workbook_profile


def _coordinate(row, column):
    letters = ""
    while column:
        column, digit = divmod(column - 1, 26)
        letters = chr(65 + digit) + letters
    return letters + str(row)


def _checkpoint(budget, checkpoint):
    if budget is not None:
        budget.checkpoint()
    if checkpoint is not None:
        checkpoint()


def _number(value):
    if isinstance(value, float):
        value = Decimal.from_float(value)
        if not value.is_finite():
            raise WorkbookError("workbook.nonfinite_binary_number")
    if isinstance(value, Decimal) and value == value.to_integral_value():
        value = int(value)
    return value, str(value)


def _xls(data, budget, checkpoint):
    xlrd = require_extra("xlrd", "excel-legacy")
    book = xlrd.open_workbook(file_contents=data, formatting_info=True, on_demand=True)
    sheets = []
    try:
        for index in range(book.nsheets):
            sheet = book.sheet_by_index(index)
            if sheet.nrows * sheet.ncols > 5_000_000:
                raise WorkbookError("workbook.materialization_limit")
            if budget is not None:
                budget.charge("cells", sheet.nrows * sheet.ncols)
            cells = []
            for r in range(sheet.nrows):
                _checkpoint(budget, checkpoint)
                for c in range(sheet.ncols):
                    cell = sheet.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_EMPTY:
                        continue
                    xf = book.xf_list[cell.xf_index]
                    fmt = book.format_map.get(xf.format_key)
                    nf = fmt.format_str if fmt is not None else "General"
                    value, raw, kind = cell.value, None, "str"
                    if cell.ctype == xlrd.XL_CELL_NUMBER:
                        value, raw = _number(value)
                        kind = "n"
                    elif cell.ctype == xlrd.XL_CELL_DATE:
                        _, raw = _number(value)
                        value = xlrd.xldate_as_datetime(value, book.datemode)
                        kind = "n"
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        value, raw, kind = bool(value), str(int(value)), "b"
                    elif cell.ctype == xlrd.XL_CELL_ERROR:
                        value = xlrd.error_text_from_code.get(value, f"#ERROR:{value}")
                        raw, kind = value, "e"
                    elif cell.ctype == xlrd.XL_CELL_BLANK:
                        value, kind = None, "n"
                    else:
                        raw = value
                    cells.append(WorkbookCell(r + 1, c + 1, _coordinate(r + 1, c + 1), value, raw,
                        kind, None, nf, getattr(xf.alignment, "indent_level", 0), (), "decoded_binary"))
            merges = tuple(f"{_coordinate(r1+1,c1+1)}:{_coordinate(r2,c2)}"
                           for r1, r2, c1, c2 in sheet.merged_cells)
            sheets.append(SheetCells(sheet.name, index, sheet.nrows, sheet.ncols, tuple(cells), merges))
    finally:
        book.release_resources()
    return tuple(sheets)


def _xlsb(data, budget, checkpoint):
    pyxlsb = require_extra("pyxlsb", "excel-binary")
    sheets = []
    with pyxlsb.open_workbook(BytesIO(data)) as book:
        for index, name in enumerate(book.sheets):
            cells = []
            with book.get_sheet(index + 1) as sheet:
                for row in sheet.rows(sparse=True):
                    _checkpoint(budget, checkpoint)
                    for cell in row:
                        if cell.v is None:
                            continue
                        if budget is not None:
                            budget.charge("cells", 1)
                        value = cell.v
                        if type(value) is bool:
                            raw, kind = str(int(value)), "b"
                        elif type(value) in {int, float}:
                            value, raw = _number(value)
                            kind = "n"
                        else:
                            value, raw, kind = str(value), str(value), "str"
                        cells.append(WorkbookCell(cell.r+1, cell.c+1, _coordinate(cell.r+1, cell.c+1),
                            value, raw, kind, evidence_kind="decoded_binary"))
            cells.sort(key=lambda c: (c.row, c.column))
            sheets.append(SheetCells(name, index, max((c.row for c in cells), default=0),
                max((c.column for c in cells), default=0), tuple(cells)))
    return tuple(sheets)


def extract_workbook(payload: SourcePayload, *, series_id, issue_id, asset_id="main",
                     profile_id="workbook.cells.v1", profile_version=1, budget=None, checkpoint=None):
    if not isinstance(payload, SourcePayload):
        raise TypeError("workbook.source_payload_required")
    _checkpoint(budget, checkpoint)
    profile = workbook_profile(payload.data, budget=budget)
    if profile.kind in {"xlsx", "xlsm"}:
        cells = read_workbook_cells(payload.data, budget=budget, checkpoint=checkpoint, _profile=profile)
        sheets = cells.sheets
        qualifications = ("OOXML numeric tokens and cached formulas retained; formulas are not evaluated.",)
    elif profile.kind == "xls":
        sheets = _xls(payload.data, budget, checkpoint)
        qualifications = ("BIFF numbers retain exact decoded binary values; no source text lexeme is asserted.",
                          "XLS formula expressions are unavailable from this decoder; cached values are retained.")
    else:
        sheets = _xlsb(payload.data, budget, checkpoint)
        qualifications = ("XLSB decoder-visible values only; number formats, merges and formulas are unavailable.",
                          "Numeric date serials remain uninterpreted; binary numbers have no source text lexeme.")
    if profile.active_parts:
        qualifications += ("Active workbook parts were retained only in original bytes and never executed.",)
    if profile.external_relations:
        qualifications += ("External workbook relations were not resolved.",)
    _checkpoint(budget, checkpoint)
    return WorkbookExtract(series_id, issue_id, asset_id, payload.identity, profile.kind,
        profile_id, profile_version, sheets, (UsedInputReceipt.for_payload(payload, "source"),),
        qualifications=qualifications)
