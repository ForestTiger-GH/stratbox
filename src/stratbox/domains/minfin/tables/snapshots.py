"""The same source-local flake as typed tables for any logical dataset adapter.

Values stay exact nullable text. Converting a flake to a database snapshot does
not introduce numeric coercion, cross-source joins or new economic units.
"""
from __future__ import annotations

import json
from ..publications.context import context_document, context_from_document

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import (
    ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable,
)
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

from .contracts import FlakeColumn, FlakeRow, FlakeTable, SerializeFlakeRequest
from .flake_codec import serialize_flake, validate_flake

FLAKE_SNAPSHOT = DataContract("minfin.flake.snapshot", 2, DataRole.EXTRACTS)
_TEXT = ScalarType.TEXT
_INT = ScalarType.INT64
_METADATA = TableSchema(DataContract("minfin.flake.metadata", 2, DataRole.EXTRACTS), (
    ColumnSchema("family_id", _TEXT), ColumnSchema("source_id", _TEXT),
    ColumnSchema("original_sha256", _TEXT), ColumnSchema("original_size", _INT),
    ColumnSchema("sheet_name", _TEXT), ColumnSchema("frequency", _TEXT),
    ColumnSchema("value_basis", _TEXT), ColumnSchema("method_version", _TEXT),
    ColumnSchema("unit_hint", _TEXT), ColumnSchema("publication", _TEXT, nullable=True),
), ("source_id",))
_COLUMNS = TableSchema(DataContract("minfin.flake.columns", 1, DataRole.EXTRACTS), (
    ColumnSchema("source_column", _INT), ColumnSchema("original_header", _TEXT),
    ColumnSchema("period_id", _TEXT),
), ("source_column",))


def _rows_schema(width: int) -> TableSchema:
    return TableSchema(DataContract("minfin.flake.rows", 2, DataRole.EXTRACTS), (
        ColumnSchema("source_row", _INT), ColumnSchema("code", _TEXT), ColumnSchema("indicator", _TEXT),
        ColumnSchema("unit", _TEXT, nullable=True), ColumnSchema("scale", _TEXT, nullable=True),
        ColumnSchema("row_basis", _TEXT, nullable=True),
        *(ColumnSchema(f"value_{index}", _TEXT, nullable=True) for index in range(width)),
    ), ("source_row",))


def flake_snapshot(flake: FlakeTable, *, dataset_id: str, version_id: str,
                   inputs: tuple[UsedInputReceipt, ...] = ()) -> DatasetSnapshot:
    validate_flake(flake)
    representation = serialize_flake(SerializeFlakeRequest(flake))
    actual = UsedInputReceipt("flake", representation.identity, representation.media_type, "inline", flake.source_id)
    lineage = (actual, *(item for item in inputs if item != actual))
    tables = (
        ("metadata", TypedTable(_METADATA, ((
            flake.family_id, flake.source_id, flake.original_identity.sha256, flake.original_identity.size,
            flake.sheet_name, flake.frequency, flake.value_basis, flake.method_version, flake.unit_hint,
            json.dumps(context_document(flake.publication), sort_keys=True) if flake.publication is not None else None,
        ),))),
        ("columns", TypedTable(_COLUMNS, tuple(
            (column.source_column, column.original_header, column.period_id) for column in flake.columns))),
        ("rows", TypedTable(_rows_schema(len(flake.columns)), tuple(
            (row.source_row, row.code, row.indicator, row.unit, row.scale, row.value_basis, *row.values) for row in flake.rows))),
    )
    return DatasetSnapshot.build(dataset_id, version_id, FLAKE_SNAPSHOT, tables,
        coverage=SnapshotCoverage("unknown", "Source-local table; publisher historical inventory is unspecified."),
        inputs=lineage)


def flake_from_snapshot(snapshot: DatasetSnapshot) -> FlakeTable:
    """Require all components and exact schemas before reconstructing the domain value."""
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or
            snapshot.manifest.contract != FLAKE_SNAPSHOT or
            tuple(name for name, _ in snapshot.tables) != ("metadata", "columns", "rows")):
        raise ValueError("minfin.flake.snapshot_invalid")
    metadata, columns, rows = (snapshot.table(name) for name in ("metadata", "columns", "rows"))
    if (metadata.schema != _METADATA or len(metadata.rows) != 1 or columns.schema != _COLUMNS or
            not 1 <= len(columns.rows) <= 16_384 or rows.schema != _rows_schema(len(columns.rows))):
        raise ValueError("minfin.flake.snapshot_invalid")
    family_id, source_id, sha256, size, sheet, frequency, basis, method, unit, publication = metadata.rows[0]
    value = FlakeTable(family_id, source_id, ByteIdentity(sha256, size), sheet, frequency, basis,
        tuple(FlakeColumn(*column) for column in columns.rows),
        tuple(FlakeRow(row[0], row[1], row[2], tuple(row[6:]), row[3], row[4], row[5]) for row in rows.rows),
        method, unit, context_from_document(json.loads(publication)) if publication is not None else None)
    validate_flake(value)
    return value


__all__ = ("FLAKE_SNAPSHOT", "flake_snapshot", "flake_from_snapshot")
