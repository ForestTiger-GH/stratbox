"""Bounded binary workbook cells with exact decoded-value qualification."""
from decimal import Decimal
from io import BytesIO
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells
from .workbook_input import WorkbookError

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
    return _xlsb_stream(BytesIO(data), budget, checkpoint)


def _xlsb_stream(stream, budget, checkpoint):
    pyxlsb = require_extra("pyxlsb", "excel-binary")
    sheets = []
    with pyxlsb.open_workbook(stream) as book:
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
