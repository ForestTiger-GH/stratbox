"""Complete source-flake interchange, independent of workbook products."""
from __future__ import annotations
from datetime import date
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import TypedTable, SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from .contracts import ParsedEscrowFile, ResolvedEscrowColumn, EscrowParsedRow
from .codec import (_schema, T, I, D, B, _json, _string_tuple, _specs, _read_specs, _frame, frame_table, _check, _check_lineage, _build, SPECS)

FLAKE = DataContract("cbr.escrow.flake.snapshot", 2, DataRole.EXTRACTS)
METADATA = _schema("flake.metadata", (
    ("source_name", T, False), ("period", T, False), ("sheet_name", T, False), ("header_row", I, False),
    ("original_sha256", T, False), ("original_size", I, False), ("source_id", T, True), ("method_version", T, False),
    ("unmapped_headers", T, False),
))
COLUMNS = _schema("flake.columns", (("source_index", I, False), ("source_name", T, False), ("indicator_code", T, False)), key=("source_index",))
PARSED_ROWS = _schema("flake.rows", (("source_row_index", I, False), ("display_order", I, False), ("row_kind", T, False),
                                   ("entity_name", T, False), ("federal_district_name", T, True), ("region_number", I, True)), key=("source_row_index",))
CELLS = _schema("flake.cells", (
    ("source_row", I, False), ("source_column", I, False), ("source_header", T, False), ("indicator_code", T, True),
    ("raw_token", T, True), ("raw_kind", T, False), ("status", T, False), ("value", D, True),
    ("row_kind", T, False), ("region", T, False), ("display_order", I, False),
), key=("source_row", "source_column"))


def flake_tables(flake):
    from .parser import CELL_COLUMNS, LONG_COLUMNS, ROW_COLUMNS
    if (not isinstance(flake, ParsedEscrowFile) or flake.original_identity is None or flake.df_cells is None
            or flake.method_version != "cbr-escrow-xlsx-flake-2" or type(flake.file_date) is not str):
        raise ValueError("escrow.flake_incomplete")
    date.fromisoformat(flake.file_date)
    if flake.header_row_index < 0 or not flake.rows or not flake.resolved_columns:
        raise ValueError("escrow.flake_structure_invalid")
    metadata = TypedTable(METADATA, ((flake.source_name, flake.file_date, flake.sheet_name, flake.header_row_index,
                                    flake.original_identity.sha256, flake.original_identity.size, flake.source_id,
                                    flake.method_version, _json(list(flake.unmapped_headers))),))
    specs = tuple(column.spec for column in flake.resolved_columns)
    rows = TypedTable(PARSED_ROWS, tuple((row.source_row_index, row.display_order, row.row_kind, row.entity_name,
                                        row.federal_district_name, row.region_number) for row in flake.rows))
    cells = frame_table(flake.df_cells, CELLS)
    column_table = TypedTable(COLUMNS, tuple((column.source_index, column.source_name, column.spec.code) for column in flake.resolved_columns))
    reconstructed = _restore_flake(metadata, column_table, _specs(specs), rows, cells)
    if (tuple(flake.df_rows.columns) != ROW_COLUMNS or tuple(flake.df_long.columns) != LONG_COLUMNS
            or not flake.df_rows.equals(reconstructed.df_rows) or not flake.df_long.equals(reconstructed.df_long)):
        raise ValueError("escrow.flake_projection_mismatch")
    return (("metadata", metadata), ("columns", column_table), ("indicators", _specs(specs)), ("rows", rows), ("cells", cells))


def _restore_flake(metadata, columns, specs_table, rows_table, cells):
    from .parser import LONG_COLUMNS, _build_rows_frame, decode_cell
    import pandas as pd
    if len(metadata.rows) != 1:
        raise ValueError("escrow.snapshot_metadata_invalid")
    name, period, sheet, header, sha, size, source_id, method, unknown = metadata.rows[0]
    date.fromisoformat(period)
    if header < 0 or method != "cbr-escrow-xlsx-flake-2":
        raise ValueError("escrow.snapshot_profile_invalid")
    specs = {spec.code: spec for spec in _read_specs(specs_table)}
    resolved = [ResolvedEscrowColumn(label, index, specs[code]) for index, label, code in columns.rows]
    rows = [EscrowParsedRow(*row) for row in rows_table.rows]
    by_row = {header + row.source_row_index + 2: row for row in rows}
    by_column = {column.source_index + 1: column for column in resolved}
    if not rows or any(row.source_row_index < 0 or row.display_order != i + 1 for i, row in enumerate(rows)):
        raise ValueError("escrow.snapshot_rows_invalid")
    if len({row.entity_name for row in rows}) != len(rows):
        raise ValueError("escrow.duplicate_region")
    if any(row.row_kind not in {"region", "federal_district", "rf_total"} for row in rows):
        raise ValueError("escrow.snapshot_rows_invalid")
    records = []
    mapped_coordinates = set()
    for source_row, source_column, label, code, token, kind, status, value, row_kind, region, display in cells.rows:
        row = by_row.get(source_row)
        if row is None or (row.row_kind, row.entity_name, row.display_order) != (row_kind, region, display) or source_column < 3:
            raise ValueError("escrow.snapshot_cell_coordinates_invalid")
        if status not in {"numeric", "blank", "marker", "unparsed", "formula_unresolved"} or kind not in {"blank", "number", "text", "boolean", "datetime", "formula"}:
            raise ValueError("escrow.snapshot_cell_status_invalid")
        if (status == "numeric") != (value is not None):
            raise ValueError("escrow.snapshot_cell_value_invalid")
        if status == "numeric" and (token is None or decode_cell(token)[3] != value):
            raise ValueError("escrow.snapshot_cell_value_invalid")
        if code is None:
            if source_column in by_column:
                raise ValueError("escrow.snapshot_cell_indicator_invalid")
            continue
        column = by_column.get(source_column)
        if column is None or column.spec.code != code or column.source_name != label:
            raise ValueError("escrow.snapshot_cell_indicator_invalid")
        mapped_coordinates.add((source_row, source_column))
        if value is not None:
            records.append((row.entity_name, column.spec.canonical_name, value, period, row.row_kind, row.display_order,
                            row.federal_district_name, row.region_number, code, column.spec.value_kind, name))
    if mapped_coordinates != {(row, column) for row in by_row for column in by_column}:
        raise ValueError("escrow.snapshot_cells_incomplete")
    # Parser records follow source-column order; the same order survives replay.
    return ParsedEscrowFile(name, period, sheet, header, resolved, rows, _build_rows_frame(rows),
                            pd.DataFrame(records, columns=LONG_COLUMNS, dtype=object), unmapped_headers=_string_tuple(unknown),
                            df_cells=_frame(cells), original_identity=ByteIdentity(sha, size), source_id=source_id, method_version=method)


def flake_snapshot(flake, *, dataset_id="cbr.escrow.flake", version_id=None):
    tables = flake_tables(flake)
    receipt = UsedInputReceipt("source_workbook", flake.original_identity,
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", flake.source_id)
    return _build(dataset_id, version_id, FLAKE, tables,
                  coverage=SnapshotCoverage("unknown", "One publication-local XLSX table; publisher historical coverage is unspecified."), inputs=(receipt,))


def flake_from_snapshot(snapshot):
    components = {"metadata": METADATA, "columns": COLUMNS, "indicators": SPECS, "rows": PARSED_ROWS, "cells": CELLS}
    _check(snapshot, FLAKE, components)
    value = _restore_flake(*(snapshot.table(name) for name in components))
    flake_tables(value)
    _check_lineage(snapshot, (UsedInputReceipt("source_workbook", value.original_identity,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", value.source_id),))
    return value
