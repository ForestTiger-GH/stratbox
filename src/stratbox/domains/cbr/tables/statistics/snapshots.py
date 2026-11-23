"""Typed, complete workbook flakes for any admitted logical dataset store."""
from dataclasses import replace
import json

from stratbox.core.formats.spreadsheets.cells import SheetCells, WorkbookCell, validate_sheet_cells
from stratbox.domains.cbr.publications.catalog import source
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, TableSchema, TypedTable
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity
from .contracts import WorkbookFlake
from .scalars import encode_scalar, decode_scalar

FLAKE = DataContract("cbr.workbook.flake", 1, DataRole.EXTRACTS)
_T, _I = ScalarType.TEXT, ScalarType.INT64
_META = TableSchema(DataContract("cbr.workbook.metadata", 1, DataRole.EXTRACTS), tuple(
    ColumnSchema(name, kind) for name, kind in (
        ("series_id", _T), ("issue_id", _T), ("source_sha256", _T), ("source_size", _I),
        ("profile_id", _T), ("profile_version", _I), ("asset_id", _T))), ("series_id", "issue_id", "asset_id"))
_SHEETS = TableSchema(DataContract("cbr.workbook.sheets", 1, DataRole.EXTRACTS), tuple(
    ColumnSchema(name, kind) for name, kind in (
        ("index", _I), ("name", _T), ("rows", _I), ("columns", _I), ("merged_ranges", _T))), ("index",))
_CELLS = TableSchema(DataContract("cbr.workbook.cells", 1, DataRole.EXTRACTS), (
    ColumnSchema("sheet", _I), ColumnSchema("row", _I), ColumnSchema("column", _I),
    ColumnSchema("coordinate", _T), ColumnSchema("value_type", _T), ColumnSchema("value", _T),
    ColumnSchema("raw_token", _T, True), ColumnSchema("kind", _T), ColumnSchema("formula", _T, True),
    ColumnSchema("number_format", _T), ColumnSchema("indent", _I), ColumnSchema("formula_attributes", _T),
), ("sheet", "row", "column"))


def flake_snapshot(value: WorkbookFlake, *, dataset_id=None, version_id=None):
    if not isinstance(value, WorkbookFlake):
        raise ValueError("cbr.workbook.flake_required")
    asset = SourceAssetIdentity(value.series_id, value.issue_id, value.asset_id)
    series = source(value.series_id)
    if (value.profile_id != series.table_profile or value.profile_version != 1 or "xlsx" not in series.formats
            or not value.issue_id or not value.sheets or value.source_identity.size == 0
            or tuple(sheet.index for sheet in value.sheets) != tuple(range(len(value.sheets)))
            or len({sheet.name for sheet in value.sheets}) != len(value.sheets)
            or not any(item.identity == value.source_identity and item.source_id in {None, value.series_id, asset.source_id}
                       for item in value.lineage)):
        raise ValueError("cbr.workbook.flake_binding_invalid")
    for sheet in value.sheets:
        validate_sheet_cells(sheet)
    meta = TypedTable(_META, ((value.series_id, value.issue_id, value.source_identity.sha256,
                              value.source_identity.size, value.profile_id, value.profile_version, value.asset_id),))
    sheets = TypedTable(_SHEETS, tuple((sheet.index, sheet.name, sheet.rows, sheet.columns,
                                     canonical_manifest_bytes(sheet.merged_ranges).decode()) for sheet in value.sheets))
    cells = TypedTable(_CELLS, tuple((sheet.index, cell.row, cell.column, cell.coordinate,
        *encode_scalar(cell.value), cell.raw_token, cell.kind, cell.formula, cell.number_format,
        cell.indent, canonical_manifest_bytes(cell.formula_attributes).decode())
        for sheet in value.sheets for cell in sheet.cells))
    result = DatasetSnapshot.build(dataset_id or value.series_id, version_id or "content", FLAKE,
        (("metadata", meta), ("sheets", sheets), ("cells", cells)), coverage=value.coverage, inputs=value.lineage)
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def _coordinate(row, column):
    result = ""
    while column:
        column, digit = divmod(column - 1, 26)
        result = chr(65 + digit) + result
    return result + str(row)


def flake_from_snapshot(snapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != FLAKE
            or tuple(name for name, _ in snapshot.tables) != ("metadata", "sheets", "cells")):
        raise ValueError("cbr.workbook.snapshot_invalid")
    meta, sheets, cells = (snapshot.table(name) for name in ("metadata", "sheets", "cells"))
    if meta.schema != _META or sheets.schema != _SHEETS or cells.schema != _CELLS or len(meta.rows) != 1:
        raise ValueError("cbr.workbook.snapshot_schema_invalid")
    series, issue, sha, size, profile, edition, asset = meta.rows[0]
    if edition != 1:
        raise ValueError("cbr.workbook.snapshot_edition_unsupported")
    grouped = {row[0]: [] for row in sheets.rows}
    if tuple(grouped) != tuple(range(len(grouped))) or len({row[1] for row in sheets.rows}) != len(sheets.rows):
        raise ValueError("cbr.workbook.snapshot_sheets_invalid")
    for item in cells.rows:
        index, row, column, coordinate, scalar, token, raw, kind, formula, fmt, indent, attributes = item
        if index not in grouped or not 1 <= row <= 1_048_576 or not 1 <= column <= 16_384 or coordinate != _coordinate(row, column):
            raise ValueError("cbr.workbook.snapshot_cell_invalid")
        attrs = json.loads(attributes)
        if (not isinstance(attrs, list) or any(not isinstance(pair, list) or len(pair) != 2
                or any(type(part) is not str for part in pair) for pair in attrs)):
            raise ValueError("cbr.workbook.snapshot_cell_invalid")
        grouped[index].append(WorkbookCell(row, column, coordinate, decode_scalar(scalar, token), raw,
            kind, formula, fmt, indent, tuple(tuple(pair) for pair in attrs)))
    values = []
    for index, name, rows, columns, ranges in sheets.rows:
        if (rows < 0 or columns < 0 or rows * columns > 5_000_000 or any(cell.row > rows or cell.column > columns
                for cell in grouped[index])):
            raise ValueError("cbr.workbook.snapshot_extent_invalid")
        merges = json.loads(ranges)
        if not isinstance(merges, list) or any(type(item) is not str for item in merges):
            raise ValueError("cbr.workbook.snapshot_sheets_invalid")
        values.append(SheetCells(name, index, rows, columns, tuple(grouped[index]), tuple(merges)))
    result = WorkbookFlake(series, issue, ByteIdentity(sha, size), profile, edition, tuple(values),
                           snapshot.manifest.inputs, snapshot.manifest.coverage, asset)
    rebuilt = flake_snapshot(result, dataset_id=snapshot.manifest.dataset_id, version_id=snapshot.manifest.version_id)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("cbr.workbook.snapshot_noncanonical")
    return result
