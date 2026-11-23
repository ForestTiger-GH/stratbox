"""Portable physical worksheet evidence, independent of decoder and publisher."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import re

from stratbox.shared.identity import ByteIdentity

class WorkbookCellsError(ValueError):
    """Invalid physical worksheet evidence."""


@dataclass(frozen=True, slots=True)
class WorkbookCell:
    row: int
    column: int
    coordinate: str
    value: int | Decimal | str | bool | date | datetime | time | timedelta | None
    raw_token: str | None
    kind: str
    formula: str | None = None
    number_format: str = "General"
    indent: int = 0
    formula_attributes: tuple[tuple[str, str], ...] = ()
    evidence_kind: str = "source_lexeme"


@dataclass(frozen=True, slots=True)
class SheetCells:
    name: str
    index: int
    rows: int
    columns: int
    cells: tuple[WorkbookCell, ...]
    merged_ranges: tuple[str, ...] = ()

    def cell(self, row: int, column: int) -> WorkbookCell | None:
        return next((cell for cell in self.cells if cell.row == row and cell.column == column), None)

    def values(self) -> tuple[tuple[object, ...], ...]:
        """Materialize the admitted rectangular extent, retaining blank cells."""
        if self.rows * self.columns > 5_000_000:
            raise WorkbookCellsError("workbook.dense_materialization_limit")
        grid = [[None] * self.columns for _ in range(self.rows)]
        for cell in self.cells:
            grid[cell.row - 1][cell.column - 1] = cell.value
        return tuple(tuple(row) for row in grid)


@dataclass(frozen=True, slots=True)
class WorkbookCells:
    sheets: tuple[SheetCells, ...]
    identity: ByteIdentity


def validate_sheet_cells(sheet: SheetCells, *, checkpoint=None) -> None:
    """Validate retained cell evidence independently of an Excel decoder."""
    if (not isinstance(sheet, SheetCells) or not sheet.name or len(sheet.name) > 255
            or type(sheet.index) is not int or sheet.index < 0 or type(sheet.rows) is not int
            or type(sheet.columns) is not int or not 0 <= sheet.rows <= 1_048_576
            or not 0 <= sheet.columns <= 16_384 or len(sheet.cells) > 5_000_000):
        raise WorkbookCellsError("workbook.cells.sheet_invalid")
    def position(coordinate):
        match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", coordinate)
        if match is None:
            raise WorkbookCellsError("workbook.cells.coordinate_invalid")
        column = 0
        for char in match[1]:
            column = column * 26 + ord(char) - 64
        row = int(match[2])
        if row > 1_048_576 or column > 16_384:
            raise WorkbookCellsError("workbook.cells.coordinate_invalid")
        return row, column
    seen = set()
    previous = (0, 0)
    for index, cell in enumerate(sheet.cells):
        if checkpoint is not None and index % 256 == 0:
            checkpoint()
        if (not isinstance(cell, WorkbookCell) or cell.kind not in {"n", "s", "str", "inlineStr", "b", "d", "e"}
                or type(cell.indent) is not int or not 0 <= cell.indent <= 250
                or not isinstance(cell.number_format, str) or len(cell.number_format) > 4096
                or cell.raw_token is not None and not isinstance(cell.raw_token, str)
                or cell.formula is not None and not isinstance(cell.formula, str)
                or cell.evidence_kind not in {"source_lexeme", "decoded_binary"}):
            raise WorkbookCellsError("workbook.cells.invalid_cell")
        point = (cell.row, cell.column)
        if (point != position(cell.coordinate) or point in seen or point <= previous
                or cell.row > sheet.rows or cell.column > sheet.columns):
            raise WorkbookCellsError("workbook.cells.coordinate_invalid")
        seen.add(point)
        previous = point
        if (not isinstance(cell.formula_attributes, tuple)
                or any(not isinstance(pair, tuple) or len(pair) != 2 or any(type(x) is not str for x in pair)
                       for pair in cell.formula_attributes)
                or len({key for key, _ in cell.formula_attributes}) != len(cell.formula_attributes)
                or cell.formula is None and cell.formula_attributes):
            raise WorkbookCellsError("workbook.cells.formula_invalid")
        if cell.kind == "n" and type(cell.value) in {int, Decimal}:
            try:
                if cell.raw_token is None or Decimal(cell.raw_token) != cell.value or not Decimal(cell.raw_token).is_finite():
                    raise ValueError
            except (ValueError, InvalidOperation):
                raise WorkbookCellsError("workbook.cells.numeric_evidence_mismatch") from None
        if cell.kind == "b" and (cell.raw_token not in {"0", "1"} or type(cell.value) is not bool
                                  or cell.value != (cell.raw_token == "1")):
            raise WorkbookCellsError("workbook.cells.boolean_evidence_mismatch")
        if cell.kind in {"s", "str", "inlineStr", "e"} and cell.value is not None and type(cell.value) is not str:
            raise WorkbookCellsError("workbook.cells.text_evidence_mismatch")
        if cell.kind == "s" and (cell.raw_token is None or not cell.raw_token.isdigit()):
            raise WorkbookCellsError("workbook.cells.string_index_invalid")
    for reference in sheet.merged_ranges:
        parts = reference.split(":")
        if len(parts) != 2:
            raise WorkbookCellsError("workbook.cells.merge_invalid")
        first, last = map(position, parts)
        if first[0] > last[0] or first[1] > last[1]:
            raise WorkbookCellsError("workbook.cells.merge_invalid")

