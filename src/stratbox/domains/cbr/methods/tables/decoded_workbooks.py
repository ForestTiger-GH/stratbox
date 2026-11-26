"""Iterate validated physical workbook cells in a declared formula-value mode."""
from stratbox.shared.data.workbook_cells import WorkbookCells, validate_sheet_cells
from stratbox.shared.identity import ByteIdentity


def decoded_sheets(workbook, original, *, formulas=False, checkpoint=None):
    """Return named row iterators without opening or converting a workbook.

    Cached mode exposes the decoder's typed cached values. Formula mode exposes
    source formula text with its equals sign; the WorkbookCells input retains
    caches, lexical tokens and formula attributes independently of that view.
    """
    identity = original if isinstance(original, ByteIdentity) else ByteIdentity.of(original)
    if (not isinstance(workbook, WorkbookCells) or workbook.identity != identity
            or not workbook.sheets or tuple(sheet.index for sheet in workbook.sheets) != tuple(range(len(workbook.sheets)))
            or len({sheet.name for sheet in workbook.sheets}) != len(workbook.sheets)):
        raise ValueError('cbr.workbook.decoded_identity_mismatch')
    def rows(sheet):
        occupied = tuple(cell for cell in sheet.cells
            if cell.value is not None or cell.raw_token is not None or cell.formula is not None)
        height = max((cell.row for cell in occupied), default=0)
        width = max((cell.column for cell in occupied), default=0)
        if height * width > 5_000_000:
            raise ValueError('cbr.workbook.interpretation_extent_limit')
        cells = iter(sheet.cells)
        cell = next(cells, None)
        for number in range(1, height + 1):
            if checkpoint is not None:
                checkpoint()
            row = [None] * width
            while cell is not None and cell.row == number:
                if cell.column <= width:
                    row[cell.column - 1] = '=' + cell.formula if formulas and cell.formula is not None else cell.value
                cell = next(cells, None)
            yield tuple(row)
    result = []
    for sheet in workbook.sheets:
        validate_sheet_cells(sheet, checkpoint=checkpoint)
        result.append((sheet.name, rows(sheet)))
    return tuple(result)
