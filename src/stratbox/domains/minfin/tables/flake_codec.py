"""Lossless, bounded source-local flake interchange independent of its store.

The JSON preserves source coordinates and evidence, including mixed unit hints.
The CSV export is intentionally a separate, human-facing representation.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import re
from decimal import Decimal, InvalidOperation
from ..publications.context import context_document, context_from_document

from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from .contracts import FlakeColumn, FlakeRow, FlakeTable, ReadFlakeRequest, SerializeFlakeRequest

PROFILE = "minfin.flake.json"
VERSION = 2
MAX_BYTES = 64 * 1024 * 1024
MAX_CELLS = 500_000
_ID = re.compile(r"[a-z][a-z0-9_.-]{2,127}\Z")
_PERIOD = {
    "monthly": re.compile(r"(?:19|20|21)\d{2}-(?:0[1-9]|1[0-2])\Z"),
    "quarterly": re.compile(r"(?:19|20|21)\d{2}-Q[1-4]\Z"),
    "annual": re.compile(r"(?:19|20|21)\d{2}\Z"),
}


def _text(value: object, *, limit: int = 32_767, empty: bool = False) -> bool:
    return isinstance(value, str) and (empty or bool(value)) and len(value) <= limit


def validate_flake(value: FlakeTable) -> None:
    """Validate the schema without applying today's calculation profile to history."""
    if (not isinstance(value, FlakeTable) or
            not isinstance(value.family_id, str) or not _ID.fullmatch(value.family_id) or
            not value.family_id.startswith("minfin.") or
            not isinstance(value.source_id, str) or not _ID.fullmatch(value.source_id) or
            not value.source_id.startswith(value.family_id + ".") or
            not isinstance(value.original_identity, ByteIdentity) or
            type(value.original_identity.size) is not int or value.original_identity.size <= 0 or
            not _text(value.sheet_name, limit=255) or
            not isinstance(value.frequency, str) or value.frequency not in _PERIOD or
            not isinstance(value.value_basis, str) or value.value_basis not in {"ytd", "annual", "stock"} or
            not _text(value.method_version, limit=128) or not _text(value.unit_hint, limit=128) or
            not isinstance(value.columns, tuple) or not 1 <= len(value.columns) <= 16_384 or
            not isinstance(value.rows, tuple) or not 1 <= len(value.rows) <= 1_048_576 or
            len(value.columns) * len(value.rows) > MAX_CELLS):
        raise ValueError("minfin.flake.representation_invalid")
    if value.publication is not None and value.publication.series_id != value.source_id:
        raise ValueError("minfin.publication_source_mismatch")
    source_columns = set()
    periods = []
    for column in value.columns:
        if (not isinstance(column, FlakeColumn) or type(column.source_column) is not int or
                not 1 <= column.source_column <= 16_384 or column.source_column in source_columns or
                not _text(column.original_header, empty=True) or
                not isinstance(column.period_id, str) or not _PERIOD[value.frequency].fullmatch(column.period_id)):
            raise ValueError("minfin.flake.representation_invalid")
        source_columns.add(column.source_column)
        periods.append(column.period_id)
    if periods != sorted(set(periods)):
        raise ValueError("minfin.flake.representation_invalid")
    source_rows = set()
    for row in value.rows:
        if (not isinstance(row, FlakeRow) or type(row.source_row) is not int or
                not 1 <= row.source_row <= 1_048_576 or row.source_row in source_rows or
                not _text(row.code, empty=True) or not _text(row.indicator) or
                not isinstance(row.values, tuple) or len(row.values) != len(value.columns) or
                any(item is not None and not _text(item, empty=True) for item in row.values)):
            raise ValueError("minfin.flake.representation_invalid")
        if (any(item is not None and not _text(item, limit=128) for item in (row.unit, row.scale, row.value_basis))
                or (row.unit is None) != (row.scale is None)
                or row.value_basis not in {None, "stock", "ytd", "annual", "period_flow", "ratio", "index", "count"}):
            raise ValueError("minfin.flake.row_semantics_invalid")
        if row.scale is not None:
            try:
                if not Decimal(row.scale).is_finite() or Decimal(row.scale) <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                raise ValueError("minfin.flake.row_semantics_invalid") from None
        source_rows.add(row.source_row)


def serialize_flake(request: SerializeFlakeRequest) -> Representation:
    value = request.flake
    validate_flake(value)
    document = {"schema": "minfin.flake.v2", **asdict(value)}
    document["publication"] = context_document(value.publication)
    data = canonical_manifest_bytes(document)
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError("minfin.representation_size_invalid")
    return Representation(PROFILE, VERSION, "application/json", data, "utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("minfin.flake.representation_invalid")
        result[key] = value
    return result


def read_flake(request: ReadFlakeRequest) -> FlakeTable:
    representation = request.representation
    if (not isinstance(representation, Representation) or type(representation.version) is not int or
            (representation.profile_id, representation.version, representation.media_type, representation.encoding)
            != (PROFILE, VERSION, "application/json", "utf-8") or
            not 0 < len(representation.data) <= MAX_BYTES):
        raise ValueError("minfin.flake.representation_invalid")
    try:
        document = json.loads(representation.data.decode("utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(document, dict) or set(document) != {
            "schema", "family_id", "source_id", "original_identity", "sheet_name",
            "frequency", "value_basis", "columns", "rows", "method_version", "unit_hint", "publication",
        } or document["schema"] != "minfin.flake.v2":
            raise ValueError("minfin.flake.representation_invalid")
        origin = document["original_identity"]
        if (not isinstance(origin, dict) or set(origin) != {"sha256", "size"} or
                not isinstance(origin["sha256"], str) or type(origin["size"]) is not int):
            raise ValueError("minfin.flake.representation_invalid")
        columns = document["columns"]
        rows = document["rows"]
        if (not isinstance(columns, list) or not 1 <= len(columns) <= 16_384 or
                not isinstance(rows, list) or not 1 <= len(rows) <= 1_048_576 or
                len(columns) * len(rows) > MAX_CELLS):
            raise ValueError("minfin.flake.representation_invalid")
        if any(not isinstance(column, dict) or set(column) != {
            "source_column", "original_header", "period_id",
        } for column in columns):
            raise ValueError("minfin.flake.representation_invalid")
        if any(not isinstance(row, dict) or set(row) != {
            "source_row", "code", "indicator", "values", "unit", "scale", "value_basis",
        } or not isinstance(row["values"], list) for row in rows):
            raise ValueError("minfin.flake.representation_invalid")
        value = FlakeTable(
            document["family_id"], document["source_id"], ByteIdentity(**origin),
            document["sheet_name"], document["frequency"], document["value_basis"],
            tuple(FlakeColumn(**column) for column in columns),
            tuple(FlakeRow(row["source_row"], row["code"], row["indicator"], tuple(row["values"]),
                           row["unit"], row["scale"], row["value_basis"]) for row in rows),
            document["method_version"], document["unit_hint"], context_from_document(document["publication"]),
        )
        validate_flake(value)
        return value
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        raise ValueError("minfin.flake.representation_invalid") from None


__all__ = ("serialize_flake", "read_flake", "validate_flake")
