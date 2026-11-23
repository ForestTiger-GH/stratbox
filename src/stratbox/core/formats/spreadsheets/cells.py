"""Bounded OOXML cells with exact numeric lexemes and cached formula evidence.

This reader assigns no business meaning to headers, sheets, dates or missing
values. Formula expressions are retained as data and are never evaluated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from posixpath import normpath
import re
from zipfile import ZipFile

from stratbox.core.formats.xml import parse_xml
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.identity import ByteIdentity
from .workbook_input import WorkbookError, workbook_profile

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


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
        grid = [[None] * self.columns for _ in range(self.rows)]
        for cell in self.cells:
            grid[cell.row - 1][cell.column - 1] = cell.value
        return tuple(tuple(row) for row in grid)


@dataclass(frozen=True, slots=True)
class WorkbookCells:
    sheets: tuple[SheetCells, ...]
    identity: ByteIdentity


def validate_sheet_cells(sheet: SheetCells) -> None:
    """Validate retained cell evidence independently of an Excel decoder."""
    if (not isinstance(sheet, SheetCells) or not sheet.name or len(sheet.name) > 255
            or type(sheet.index) is not int or sheet.index < 0 or type(sheet.rows) is not int
            or type(sheet.columns) is not int or not 0 <= sheet.rows <= 1_048_576
            or not 0 <= sheet.columns <= 16_384 or sheet.rows * sheet.columns > 5_000_000):
        raise WorkbookError("workbook.cells.sheet_invalid")
    def position(coordinate):
        match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", coordinate)
        if match is None:
            raise WorkbookError("workbook.cells.coordinate_invalid")
        column = 0
        for char in match[1]:
            column = column * 26 + ord(char) - 64
        row = int(match[2])
        if row > 1_048_576 or column > 16_384:
            raise WorkbookError("workbook.cells.coordinate_invalid")
        return row, column
    seen = set()
    previous = (0, 0)
    for cell in sheet.cells:
        if (not isinstance(cell, WorkbookCell) or cell.kind not in {"n", "s", "str", "inlineStr", "b", "d", "e"}
                or type(cell.indent) is not int or not 0 <= cell.indent <= 250
                or not isinstance(cell.number_format, str) or len(cell.number_format) > 4096
                or cell.raw_token is not None and not isinstance(cell.raw_token, str)
                or cell.formula is not None and not isinstance(cell.formula, str)):
            raise WorkbookError("workbook.cells.invalid_cell")
        point = (cell.row, cell.column)
        if (point != position(cell.coordinate) or point in seen or point <= previous
                or cell.row > sheet.rows or cell.column > sheet.columns):
            raise WorkbookError("workbook.cells.coordinate_invalid")
        seen.add(point)
        previous = point
        if (not isinstance(cell.formula_attributes, tuple)
                or any(not isinstance(pair, tuple) or len(pair) != 2 or any(type(x) is not str for x in pair)
                       for pair in cell.formula_attributes)
                or len({key for key, _ in cell.formula_attributes}) != len(cell.formula_attributes)
                or cell.formula is None and cell.formula_attributes):
            raise WorkbookError("workbook.cells.formula_invalid")
        if cell.kind == "n" and type(cell.value) in {int, Decimal}:
            try:
                if cell.raw_token is None or Decimal(cell.raw_token) != cell.value or not Decimal(cell.raw_token).is_finite():
                    raise ValueError
            except (ValueError, InvalidOperation):
                raise WorkbookError("workbook.cells.numeric_evidence_mismatch") from None
        if cell.kind == "b" and (cell.raw_token not in {"0", "1"} or type(cell.value) is not bool
                                  or cell.value != (cell.raw_token == "1")):
            raise WorkbookError("workbook.cells.boolean_evidence_mismatch")
        if cell.kind in {"s", "str", "inlineStr", "e"} and cell.value is not None and type(cell.value) is not str:
            raise WorkbookError("workbook.cells.text_evidence_mismatch")
        if cell.kind == "s" and (cell.raw_token is None or not cell.raw_token.isdigit()):
            raise WorkbookError("workbook.cells.string_index_invalid")
    for reference in sheet.merged_ranges:
        parts = reference.split(":")
        if len(parts) != 2:
            raise WorkbookError("workbook.cells.merge_invalid")
        first, last = map(position, parts)
        if first[0] > last[0] or first[1] > last[1]:
            raise WorkbookError("workbook.cells.merge_invalid")


def _text(element):
    if element is None:
        return ""
    # Phonetic annotations do not belong to the visible cell text.
    return "".join(node.text or "" for child in element
                   if child.tag != _NS + "rPh" for node in child.iter(_NS + "t"))


def read_workbook_cells(data: bytes, *, budget=None) -> WorkbookCells:
    """Read every worksheet of an admitted XLSX without float coercion.

    Date serials use the workbook epoch and number format; their exact serial
    remains in ``raw_token``. Empty cached formula values remain unknown.
    """
    profile = workbook_profile(data, budget=budget)
    if profile.kind != "xlsx":
        raise WorkbookError("workbook.cells.xlsx_required")
    profile.check_materialization(budget)
    require_extra("openpyxl", "excel")
    from openpyxl.styles.numbers import BUILTIN_FORMATS, is_date_format, is_timedelta_format
    from openpyxl.utils.cell import coordinate_to_tuple
    from openpyxl.utils.datetime import CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900, from_excel

    with ZipFile(BytesIO(data)) as package:
        def xml(name):
            return parse_xml(package.read(name))

        workbook = xml("xl/workbook.xml")
        if workbook.tag != _NS + "workbook":
            raise WorkbookError("workbook.cells.namespace_unsupported")
        rels = {node.get("Id"): node for node in xml("xl/_rels/workbook.xml.rels")}
        strings = ()
        if "xl/sharedStrings.xml" in package.namelist():
            strings = tuple(_text(item) for item in xml("xl/sharedStrings.xml"))
        formats, styles = dict(BUILTIN_FORMATS), [("General", 0)]
        if "xl/styles.xml" in package.namelist():
            root = xml("xl/styles.xml")
            formats.update({int(node.get("numFmtId")): node.get("formatCode", "General")
                            for node in root.findall(_NS + "numFmts/" + _NS + "numFmt")})
            styles = []
            for node in root.findall(_NS + "cellXfs/" + _NS + "xf"):
                alignment = node.find(_NS + "alignment")
                styles.append((formats.get(int(node.get("numFmtId", "0")), "General"),
                               int(alignment.get("indent", "0")) if alignment is not None else 0))
            styles = styles or [("General", 0)]
        properties = workbook.find(_NS + "workbookPr")
        epoch = CALENDAR_MAC_1904 if properties is not None and properties.get("date1904") in {"1", "true"} else CALENDAR_WINDOWS_1900
        sheets = []
        for index, sheet in enumerate(workbook.findall(_NS + "sheets/" + _NS + "sheet")):
            relation = rels.get(sheet.get(_REL + "id"))
            if relation is None or relation.get("TargetMode") == "External":
                raise WorkbookError("workbook.cells.sheet_relation_invalid")
            target = relation.get("Target", "")
            path = normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
            if not path.startswith("xl/") or path not in package.namelist():
                raise WorkbookError("workbook.cells.sheet_relation_invalid")
            root = xml(path)
            if root.tag != _NS + "worksheet":
                raise WorkbookError("workbook.cells.sheet_kind_unsupported")
            cells, positions = [], set()
            for node in root.findall(_NS + "sheetData/" + _NS + "row/" + _NS + "c"):
                coordinate = node.get("r", "")
                try:
                    row, column = coordinate_to_tuple(coordinate)
                    if (row, column) in positions or not 1 <= row <= 1_048_576 or not 1 <= column <= 16_384:
                        raise ValueError
                    positions.add((row, column))
                    style_index = int(node.get("s", "0"))
                    if style_index < 0:
                        raise ValueError
                    number_format, indent = styles[style_index]
                    kind = node.get("t", "n")
                    raw = node.findtext(_NS + "v")
                    formula_node = node.find(_NS + "f")
                    formula = (formula_node.text or "") if formula_node is not None else None
                    attrs = tuple(sorted(formula_node.attrib.items())) if formula_node is not None else ()
                    if kind == "inlineStr":
                        value = _text(node.find(_NS + "is"))
                    elif raw is None or raw == "":
                        value = None
                    elif kind == "s":
                        if not raw.isdigit():
                            raise ValueError
                        value = strings[int(raw)]
                    elif kind in {"str", "e"}:
                        value = raw
                    elif kind == "b":
                        if raw not in {"0", "1"}:
                            raise ValueError
                        value = raw == "1"
                    elif kind == "d":
                        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    elif kind == "n":
                        numeric = Decimal(raw)
                        if not numeric.is_finite():
                            raise ValueError
                        if is_timedelta_format(number_format):
                            value = from_excel(float(numeric), epoch, timedelta=True)
                        elif is_date_format(number_format):
                            value = from_excel(float(numeric), epoch)
                        else:
                            value = int(raw) if raw.lstrip("-+").isdigit() else numeric
                    else:
                        raise ValueError
                except (ValueError, TypeError, IndexError, KeyError, InvalidOperation, OverflowError):
                    raise WorkbookError("workbook.cells.invalid_cell") from None
                cells.append(WorkbookCell(row, column, coordinate, value, raw, kind,
                                          formula, number_format, indent, attrs))
                if budget is not None:
                    budget.checkpoint()
            cells.sort(key=lambda cell: (cell.row, cell.column))
            rows = max((cell.row for cell in cells), default=0)
            columns = max((cell.column for cell in cells), default=0)
            if rows * columns > 5_000_000:
                raise WorkbookError("workbook.materialization_limit")
            merges = tuple(node.get("ref", "") for node in root.findall(_NS + "mergeCells/" + _NS + "mergeCell"))
            value = SheetCells(sheet.get("name", ""), index, rows, columns, tuple(cells), merges)
            validate_sheet_cells(value)
            sheets.append(value)
    if not sheets or len({sheet.name for sheet in sheets}) != len(sheets):
        raise WorkbookError("workbook.cells.sheets_invalid")
    return WorkbookCells(tuple(sheets), ByteIdentity.of(data))
