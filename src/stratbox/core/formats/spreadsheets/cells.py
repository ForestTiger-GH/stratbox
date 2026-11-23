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


from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells, WorkbookCells
from stratbox.shared.data.workbook_cells import validate_sheet_cells as _validate_sheet_cells


def validate_sheet_cells(sheet, *, checkpoint=None):
    try:
        _validate_sheet_cells(sheet, checkpoint=checkpoint)
    except ValueError as exc:
        raise WorkbookError(str(exc)) from None


def _text(element):
    if element is None:
        return ""
    # Phonetic annotations do not belong to the visible cell text.
    return "".join(node.text or "" for child in element
                   if child.tag != _NS + "rPh" for node in child.iter(_NS + "t"))


def read_workbook_cells(data: bytes, *, budget=None, checkpoint=None, _profile=None) -> WorkbookCells:
    """Read every worksheet of an admitted XLSX without float coercion.

    Date serials use the workbook epoch and number format; their exact serial
    remains in ``raw_token``. Absent caches remain unknown; an explicit empty
    cached string remains an empty string.
    """
    profile = _profile if _profile is not None else workbook_profile(data, budget=budget)
    if profile.kind not in {"xlsx", "xlsm"}:
        raise WorkbookError("workbook.cells.ooxml_required")
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
                    raw_node = node.find(_NS + "v")
                    raw = raw_node.text if raw_node is not None else None
                    formula_node = node.find(_NS + "f")
                    formula = (formula_node.text or "") if formula_node is not None else None
                    attrs = tuple(sorted(formula_node.attrib.items())) if formula_node is not None else ()
                    if kind == "inlineStr":
                        value = _text(node.find(_NS + "is"))
                    elif kind in {"str", "e"} and raw_node is not None:
                        raw = raw or ""
                        value = raw
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
                if checkpoint is not None:
                    checkpoint()
            cells.sort(key=lambda cell: (cell.row, cell.column))
            rows = max((cell.row for cell in cells), default=0)
            columns = max((cell.column for cell in cells), default=0)
            if len(cells) > 5_000_000:
                raise WorkbookError("workbook.materialization_limit")
            merges = tuple(node.get("ref", "") for node in root.findall(_NS + "mergeCells/" + _NS + "mergeCell"))
            dimension = root.find(_NS + "dimension")
            extents = (*merges, *((dimension.get("ref", ""),) if dimension is not None else ()))
            for extent in extents:
                if not extent:
                    continue
                for coordinate in extent.split(":"):
                    try:
                        r, c = coordinate_to_tuple(coordinate)
                        if not 1 <= r <= 1_048_576 or not 1 <= c <= 16_384:
                            raise ValueError
                    except (ValueError, TypeError, KeyError):
                        raise WorkbookError("workbook.cells.extent_invalid") from None
                    rows, columns = max(rows, r), max(columns, c)
            value = SheetCells(sheet.get("name", ""), index, rows, columns, tuple(cells), merges)
            validate_sheet_cells(value)
            sheets.append(value)
    if not sheets or len({sheet.name for sheet in sheets}) != len(sheets):
        raise WorkbookError("workbook.cells.sheets_invalid")
    return WorkbookCells(tuple(sheets), ByteIdentity.of(data))
