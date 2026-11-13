"""Workbook admission by actual format and limits shared across decoders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from io import BytesIO
from math import isfinite
from posixpath import dirname, join, normpath
from struct import error as StructError, unpack_from
import re
from typing import Callable, Literal, Protocol
from xml.etree import ElementTree as ET

from stratbox.base.capabilities import BindingError, CapabilityRequirement, ProviderBinding, select_provider
from stratbox.base.filestore import FileStore, LocalFileStore
from stratbox.base.ioapi.archive_bytes import ArchiveError, ArchiveLimits, open_zip
from stratbox.base.ioapi.bytes import read_bounded_bytes
from stratbox.base.ioapi.xml import XmlError, inspect_xml, parse_xml
from stratbox.base.limits import BudgetMeter
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import ByteIdentity

WorkbookKind = Literal["xlsx", "xlsm", "xlsb", "xls"]
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_BIFF = (b"\x09\x00", b"\x09\x02", b"\x09\x04", b"\x09\x08")
_MAX_PACKED = 128 * 1024 * 1024
_LIMITS = ArchiveLimits(8_192, 384 * 1024 * 1024, 128 * 1024 * 1024, _MAX_PACKED)
_CELL_LIMIT = 5_000_000
_WORKBOOK_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml": "xlsx",
    "application/vnd.ms-excel.sheet.macroEnabled.main+xml": "xlsm",
    "application/vnd.ms-excel.sheet.binary.macroEnabled.main": "xlsb",
}
_ENGINES = {"xlsx": "openpyxl", "xlsm": "openpyxl", "xlsb": "pyxlsb", "xls": "xlrd"}
_EXTRAS = {"openpyxl": "excel", "pyxlsb": "excel-binary", "xlrd": "excel-legacy"}


class WorkbookError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WorkbookProfile:
    kind: WorkbookKind
    active_parts: bool
    external_relations: bool
    observed_cells: int | None
    largest_sheet_extent: int = 0

    def check_materialization(self, budget: BudgetMeter | None = None) -> None:
        if self.largest_sheet_extent > _CELL_LIMIT:
            raise WorkbookError("workbook.materialization_limit")
        if budget is not None and budget.limits.cells is not None:
            if self.largest_sheet_extent > budget.limits.cells:
                raise WorkbookError("workbook.materialization_limit")

    @property
    def decoder(self) -> str:
        return _ENGINES[self.kind]


def _legacy_profile(data, *, budget, cancelled):
    raw = data
    if data.startswith(_OLE):
        if len(data) < 512:
            raise WorkbookError("workbook.legacy_header_invalid")
        version, endian, shift, mini_shift = unpack_from("<HHHH", data, 26)
        if (version, endian, shift, mini_shift) not in {(3, 0xfffe, 9, 6), (4, 0xfffe, 12, 6)}:
            raise WorkbookError("workbook.legacy_header_invalid")
        if len(data) % (1 << shift):
            raise WorkbookError("workbook.legacy_header_invalid")
        olefile = require_extra("olefile", "excel-legacy")
        try:
            with olefile.OleFileIO(BytesIO(data), raise_defects=olefile.DEFECT_INCORRECT) as package:
                if package.exists("EncryptedPackage") or package.exists("EncryptionInfo"):
                    raise WorkbookError("workbook.encrypted")
                names = [name for name in ("Workbook", "Book") if package.exists(name)]
                if len(names) != 1:
                    raise WorkbookError("workbook.not_spreadsheet")
                size = package.get_size(names[0])
                if not 4 <= size <= len(data):
                    raise WorkbookError("workbook.legacy_stream_invalid")
                if budget is not None:
                    budget.check("decoded_bytes", size)
                with package.openstream(names[0]) as stream:
                    raw = stream.read()
                if len(raw) != size:
                    raise WorkbookError("workbook.legacy_stream_invalid")
        except (OSError, IndexError, RecursionError, StructError):
            raise WorkbookError("workbook.legacy_stream_invalid") from None
    if len(raw) < 8 or not raw.startswith(_BIFF):
        raise WorkbookError("workbook.legacy_stream_invalid")
    offset = 0
    ended = False
    if budget is not None:
        budget.charge("decoded_bytes", len(raw))
    while len(raw) - offset >= 4:
        if cancelled is not None and cancelled():
            raise WorkbookError("operation.cancelled")
        if budget is not None:
            budget.checkpoint()
        kind, length = unpack_from("<HH", raw, offset)
        if ended and kind == length == 0 and not any(memoryview(raw)[offset:]):
            offset = len(raw)
            break
        offset += 4 + length
        if offset > len(raw):
            raise WorkbookError("workbook.legacy_stream_invalid")
        if kind == 0x002f:
            raise WorkbookError("workbook.encrypted")
        ended = kind == 0x000a
    if offset != len(raw) or not ended:
        raise WorkbookError("workbook.legacy_stream_invalid")
    return WorkbookProfile("xls", False, False, None)


def _binary_records(stream, *, budget, cancelled):
    """Validate BIFF12 framing before the optional decoder allocates records."""
    def read(count):
        if cancelled is not None and cancelled():
            raise WorkbookError("operation.cancelled")
        chunk = stream.read(count)
        if budget is not None:
            budget.charge("decoded_bytes", len(chunk))
        return chunk

    def integer(first, *, bits, length):
        value = 0
        for index in range(length):
            byte = first[0]
            value |= (byte if bits == 8 else byte & 127) << (index * bits)
            if byte < 128:
                return value
            first = read(1)
            if not first:
                break
        raise WorkbookError("workbook.binary_record_invalid")

    while first := read(1):
        kind = integer(first, bits=8, length=2)
        size = read(1)
        if not size:
            raise WorkbookError("workbook.binary_record_invalid")
        length = integer(size, bits=7, length=4)
        prefix = read(min(16, length))
        if len(prefix) != min(16, length):
            raise WorkbookError("workbook.binary_record_invalid")
        yield kind, prefix
        remaining = length - len(prefix)
        while remaining:
            chunk = read(min(65536, remaining))
            if not chunk:
                raise WorkbookError("workbook.binary_record_invalid")
            remaining -= len(chunk)


def _binary_sheet(stream, *, budget, cancelled):
    # Record identifiers match the pyxlsb decoder. The cell count is measured
    # separately from its dimension hint, which controls dense allocations.
    dimension = None
    last_row, widest, cells = 0, 0, 0
    in_data = False
    row_columns: set[int] = set()
    for kind, prefix in _binary_records(stream, budget=budget, cancelled=cancelled):
        if kind == 0x0194:
            if len(prefix) != 16 or dimension is not None:
                raise WorkbookError("workbook.binary_dimension_invalid")
            r1, r2, c1, c2 = unpack_from("<IIII", prefix)
            if not (r1 <= r2 < 1_048_576 and c1 <= c2 < 16_384):
                raise WorkbookError("workbook.binary_dimension_invalid")
            dimension = (r2 + 1, c2 + 1)
        elif kind == 0x0191:
            in_data = True
        elif kind == 0x0192:
            in_data = False
        elif in_data and kind == 0:
            if len(prefix) < 4:
                raise WorkbookError("workbook.binary_record_invalid")
            row = unpack_from("<I", prefix)[0] + 1
            if not last_row < row <= 1_048_576:
                raise WorkbookError("workbook.binary_row_invalid")
            last_row = row
            row_columns.clear()
        elif in_data and 1 <= kind <= 11:
            if len(prefix) < 8 or last_row == 0:
                raise WorkbookError("workbook.binary_record_invalid")
            col = unpack_from("<I", prefix)[0] + 1
            if not 1 <= col <= 16_384 or col in row_columns:
                raise WorkbookError("workbook.binary_column_invalid")
            row_columns.add(col)
            widest = max(widest, col)
            cells += 1
            if budget is not None:
                budget.charge("cells", 1)
            if cells > _CELL_LIMIT:
                raise WorkbookError("workbook.cell_limit")
    if dimension is None or widest > dimension[1] or last_row > dimension[0]:
        raise WorkbookError("workbook.binary_dimension_invalid")
    return cells, last_row * dimension[1]


def workbook_profile(
    data: bytes, *, budget: BudgetMeter | None = None,
    depth: int = 1, cancelled: Callable[[], bool] | None = None,
    archive_limits: ArchiveLimits = _LIMITS,
) -> WorkbookProfile:
    """Check the package and scan real XML cells. Sheet dimensions are hints."""
    if not isinstance(data, bytes) or not 0 < len(data) <= min(_MAX_PACKED, archive_limits.packed_bytes):
        raise WorkbookError("workbook.size_limit")
    if not 1 <= depth <= 4:
        raise WorkbookError("archive.depth_limit")
    if data.startswith((_OLE, *_BIFF)):
        if budget is not None:
            budget.check("archive_depth", depth)
        return _legacy_profile(data, budget=budget, cancelled=cancelled)

    cells = 0
    external = False
    row_limit = column_limit = 0
    largest_extent = 0
    relation_ids: set[str] = set()
    current_part = ""

    def node(name, attributes):
        nonlocal cells, external, row_limit, column_limit
        tag = name.rsplit("}", 1)[-1]
        if tag == "Relationship" and current_part.lower().endswith(".rels"):
            reference = attributes.get("Id")
            target = attributes.get("Target")
            mode = attributes.get("TargetMode", "Internal")
            if not reference or reference in relation_ids or not target or mode not in {"External", "Internal"}:
                raise WorkbookError("workbook.relationship_invalid")
            relation_ids.add(reference)
            if mode == "External":
                external = True
            else:
                base = "" if target.startswith("/") else dirname(dirname(current_part))
                resolved = normpath(join(base, target.lstrip("/")))
                if (target.startswith("//") or resolved in {".", ".."} or resolved.startswith("../")
                        or any(char in target for char in ":\\\x00")):
                    raise WorkbookError("workbook.relationship_invalid")
                relation = attributes.get("Type", "").rsplit("/", 1)[-1]
                if relation == "worksheet":
                    suffix = ".bin" if kind == "xlsb" else ".xml"
                    if resolved not in names or not resolved.endswith(suffix):
                        raise WorkbookError("workbook.relationship_invalid")
                    if kind == "xlsb" and (resolved.count("/") != 2
                                            or not resolved.startswith("xl/worksheets/")):
                        raise WorkbookError("workbook.relationship_invalid")
        spreadsheet = name.startswith(("http://schemas.openxmlformats.org/spreadsheetml/",
                                       "http://purl.oclc.org/ooxml/spreadsheetml/"))
        if tag == "row" and spreadsheet:
            coordinate = attributes.get("r")
            if coordinate is not None and re.fullmatch(r"[1-9][0-9]{0,6}", coordinate) is None:
                raise WorkbookError("workbook.row_invalid")
            row = row_limit + 1 if coordinate is None else int(coordinate)
            if not 1 <= row <= 1_048_576:
                raise WorkbookError("workbook.row_invalid")
            row_limit = max(row_limit, row)
        if tag == "c" and spreadsheet:
            coordinate = attributes.get("r")
            if coordinate:
                cell = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", coordinate)
                if cell is None:
                    raise WorkbookError("workbook.cell_reference_invalid")
                column = 0
                for letter in cell[1]:
                    column = column * 26 + ord(letter) - 64
                row = int(cell[2])
                if not 1 <= row <= 1_048_576 or not 1 <= column <= 16_384:
                    raise WorkbookError("workbook.cell_reference_invalid")
                column_limit = max(column_limit, column)
                row_limit = max(row_limit, row)
            cells += 1
            if cells > _CELL_LIMIT:
                raise WorkbookError("workbook.cell_limit")
            if budget is not None:
                budget.charge("cells", 1)

    try:
        with open_zip(data, archive_limits, budget=budget, depth=depth) as package:
            names = set(package.namelist())
            if "[Content_Types].xml" not in names:
                raise WorkbookError("workbook.not_spreadsheet")
            with package.open("[Content_Types].xml") as stream:
                manifest = stream.read(1_048_577)
            types = parse_xml(manifest, budget=budget, limit=1_048_576)
            candidates = {
                (item.get("PartName", "").lstrip("/"), _WORKBOOK_TYPES[item.get("ContentType")])
                for item in types
                if item.get("ContentType") in _WORKBOOK_TYPES
            }
            if len(candidates) != 1:
                raise WorkbookError("workbook.not_spreadsheet")
            main, kind = next(iter(candidates))
            if main not in names or not main.endswith(".bin" if kind == "xlsb" else ".xml"):
                raise WorkbookError("workbook.missing_main_part")
            if kind == "xlsb" and main != "xl/workbook.bin":
                raise WorkbookError("workbook.missing_main_part")
            xml_parts = {
                item.get("PartName", "").lstrip("/") for item in types
                if item.get("ContentType", "").endswith(("+xml", "/xml"))
            }
            active = any(
                any(part in name.casefold() for part in (
                    "/vbaproject", "/activex/", "/embeddings/", "/macrosheets/", "/connections.",
                ))
                for name in names
            )
            binary_bytes = 0
            for name in sorted(names):
                current_part = name
                relation_ids.clear()
                row_limit = column_limit = 0
                if name != "[Content_Types].xml" and (name in xml_parts or name.lower().endswith((".xml", ".rels"))):
                    with package.open(name) as stream:
                        inspect_xml(stream, budget=budget, start=node, text_limit=131_072, cancelled=cancelled)
                    largest_extent = max(largest_extent, row_limit * column_limit)
                elif kind == "xlsb" and name.startswith("xl/worksheets/") and name.endswith(".bin"):
                    with package.open(name) as stream:
                        count, extent = _binary_sheet(stream, budget=budget, cancelled=cancelled)
                    cells += count
                    largest_extent = max(largest_extent, extent)
                    binary_bytes += package.getinfo(name).file_size
                elif kind == "xlsb" and name in {main, "xl/sharedStrings.bin"}:
                    with package.open(name) as stream:
                        for _ in _binary_records(stream, budget=budget, cancelled=cancelled):
                            pass
                    binary_bytes += package.getinfo(name).file_size
                if cells > _CELL_LIMIT:
                    raise WorkbookError("workbook.cell_limit")
            if kind == "xlsb" and budget is not None:
                budget.charge("temporary_bytes", binary_bytes)
            return WorkbookProfile(kind, active, external, cells, largest_extent)
    except (XmlError, ArchiveError) as error:
        raise WorkbookError(str(error)) from None


def read_workbook_df(
    path: str, store: FileStore | None = None, *,
    expected: WorkbookKind | None = None, budget: BudgetMeter | None = None, **options,
):
    target = store if store is not None else LocalFileStore()
    remaining = budget.remaining("input_bytes") if budget is not None else None
    limit = min(_MAX_PACKED, remaining) if remaining is not None else _MAX_PACKED
    data = read_bounded_bytes(path, store=target, limit=limit, budget=budget)
    profile = workbook_profile(data, budget=budget)
    if expected is not None and profile.kind != expected:
        raise WorkbookError("workbook.format_mismatch")
    profile.check_materialization(budget)
    engine = profile.decoder
    require_extra(engine, _EXTRAS[engine])
    pandas = require_extra("pandas", "dataframe")
    if options.keys() & {"engine", "engine_kwargs", "storage_options"}:
        raise WorkbookError("workbook.decoder_override_forbidden")
    if engine == "openpyxl":
        options["engine_kwargs"] = {"read_only": True, "data_only": True, "keep_links": False}
    return pandas.read_excel(BytesIO(data), engine=engine, **options)


@dataclass(frozen=True, slots=True)
class WorkbookPreview:
    kind: WorkbookKind
    identity: ByteIdentity
    sheets: tuple[str, ...]
    selected_sheet: str
    rows: tuple[tuple[object, ...], ...]
    truncated: bool
    value_basis: str
    start_row: int = 1
    start_column: int = 1


class WorkbookWorker(Protocol):
    """Trusted adapter to a separately constrained decoder."""

    def preview(self, data: bytes, *, sheet: str | None, start_row: int, start_column: int,
                max_rows: int, max_columns: int, budget: BudgetMeter | None) -> WorkbookPreview: ...


def _select_sheet(names, sheet):
    if not names or (sheet is not None and sheet not in names):
        raise WorkbookError("workbook.sheet_missing")
    return names[0] if sheet is None else sheet


def _preview_local(data, profile, sheet, start_row, start_column, max_rows, max_columns):
    end_row, end_column = start_row + max_rows, start_column + max_columns
    if profile.kind in {"xlsx", "xlsm"}:
        engine = require_extra("openpyxl", "excel")
        book = engine.load_workbook(
            BytesIO(data), read_only=True, data_only=True, keep_links=False, keep_vba=False,
        )
        try:
            names = tuple(book.sheetnames)
            selected = _select_sheet(names, sheet)
            table = book[selected]
            table.reset_dimensions()
            rows = tuple(table.iter_rows(
                min_row=start_row, min_col=start_column, max_row=end_row,
                max_col=end_column, values_only=True,
            ))
            return names, selected, rows, "cached_values"
        finally:
            book.close()
    if profile.kind == "xlsb":
        engine = require_extra("pyxlsb", "excel-binary")
        with engine.open_workbook(BytesIO(data)) as book:
            names = tuple(book.sheets)
            selected = _select_sheet(names, sheet)
            with book.get_sheet(selected) as table:
                rows = []
                for row in table.rows(sparse=True):
                    index = row[0].r + 1
                    if index < start_row:
                        continue
                    if index >= end_row:
                        rows.extend([()] * (max_rows + 1 - len(rows)))
                        break
                    while len(rows) < index - start_row:
                        rows.append(())
                    rows.append(tuple(cell.v for cell in row[start_column - 1:end_column]))
        return names, selected, tuple(rows), "decoder_values"
    engine = require_extra("xlrd", "excel-legacy")
    book = engine.open_workbook(file_contents=data, on_demand=True, ragged_rows=True)
    try:
        names = tuple(book.sheet_names())
        selected = _select_sheet(names, sheet)
        table = book.sheet_by_name(selected)
        rows = tuple(
            tuple(table.row_values(index, start_colx=start_column - 1,
                                   end_colx=min(table.row_len(index), end_column)))
            for index in range(start_row - 1, min(table.nrows, end_row))
        )
        return names, selected, rows, "decoder_values"
    finally:
        book.release_resources()


def preview_workbook(
    data: bytes, *, sheet: str | None = None, start_row: int = 1, start_column: int = 1, max_rows: int = 100,
    max_columns: int = 100, budget: BudgetMeter | None = None,
    worker: WorkbookWorker | None = None, require_isolation: bool = False,
    binding: ProviderBinding | None = None,
) -> WorkbookPreview:
    """Inspect a normal workbook without any domain mapping or layout template."""
    if type(max_rows) is not int or not 1 <= max_rows <= 1000:
        raise WorkbookError("workbook.preview_limit")
    if type(max_columns) is not int or not 1 <= max_columns <= 1000:
        raise WorkbookError("workbook.preview_limit")
    if (type(start_row) is not int or not 1 <= start_row <= 1_048_576
            or type(start_column) is not int or not 1 <= start_column <= 16_384
            or start_row + max_rows - 1 > 1_048_576 or start_column + max_columns - 1 > 16_384):
        raise WorkbookError("workbook.preview_range_invalid")
    if not isinstance(data, bytes) or not 0 < len(data) <= _MAX_PACKED:
        raise WorkbookError("workbook.size_limit")
    if budget is not None:
        budget.charge("input_bytes", len(data))
    if require_isolation:
        if worker is None or binding is None:
            raise WorkbookError("workbook.isolation_missing")
        requirement = CapabilityRequirement("workbook_decoder", guarantees=frozenset({"isolation_enforced"}))
        try:
            selected = select_provider(requirement, (binding,))
        except BindingError as error:
            raise WorkbookError(error.code) from None
        if selected.provider is not worker:
            raise WorkbookError("provider.binding_mismatch")
    identity = ByteIdentity.of(data)
    if worker is not None:
        value = worker.preview(data, sheet=sheet, start_row=start_row, start_column=start_column,
                               max_rows=max_rows, max_columns=max_columns, budget=budget)
        if budget is not None:
            budget.checkpoint()
        if (
            not isinstance(value, WorkbookPreview) or value.identity != identity
            or value.kind not in _ENGINES or value.selected_sheet not in value.sheets
            or (sheet is not None and value.selected_sheet != sheet)
            or type(value.start_row) is not int or value.start_row != start_row
            or type(value.start_column) is not int or value.start_column != start_column
            or type(value.sheets) is not tuple or len(value.sheets) > _LIMITS.members
            or type(value.rows) is not tuple or len(value.rows) > max_rows
            or any(type(row) is not tuple or len(row) > max_columns for row in value.rows)
        ):
            raise WorkbookError("workbook.worker_result_invalid")
        _check_preview(value, budget)
        return value
    profile = workbook_profile(data, budget=budget)
    try:
        names, selected, rows, basis = _preview_local(
            data, profile, sheet, start_row, start_column, max_rows, max_columns,
        )
    except (IndexError, KeyError, OSError, StructError) as error:
        raise WorkbookError("workbook.decoder_rejected") from error
    if budget is not None:
        budget.checkpoint()
    result = WorkbookPreview(
        profile.kind, identity, names, selected,
        tuple(row[:max_columns] for row in rows[:max_rows]),
        len(rows) > max_rows or any(any(cell is not None and cell != "" for cell in row[max_columns:]) for row in rows),
        basis, start_row, start_column,
    )
    _check_preview(result, budget)
    return result


def _check_preview(preview: WorkbookPreview, budget: BudgetMeter | None) -> None:
    if (type(preview.truncated) is not bool or preview.value_basis not in {"cached_values", "decoder_values"}
            or not all(isinstance(name, str) and 0 < len(name) <= 255 for name in preview.sheets)):
        raise WorkbookError("workbook.worker_result_invalid")
    size = 0
    for row in preview.rows:
        for value in row:
            if isinstance(value, str):
                if len(value) > 32_767:
                    raise WorkbookError("workbook.text_limit")
                size += len(value.encode("utf-8"))
            elif value is not None and (
                type(value) not in {bool, int, float, date, datetime, time, timedelta}
                or (type(value) is float and not isfinite(value))
            ):
                raise WorkbookError("workbook.worker_result_invalid")
            else:
                size += 32
            if size > 16 * 1024 * 1024:
                raise WorkbookError("workbook.preview_size_limit")
        if budget is not None:
            budget.checkpoint()
    if budget is not None:
        budget.charge("output_bytes", size)
