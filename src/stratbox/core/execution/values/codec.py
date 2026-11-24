"""Bounded, versioned value snapshots without executable deserialization."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import base64
import json

from stratbox.core.storage.datasets.codec import (
    contract_from, decode_table, encode_table, identity_from, loads, manifest_from,
)
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable, contract_value, identity_value, manifest_value
from stratbox.shared.data.workbook_cells import WorkbookCell, WorkbookCells, SheetCells, validate_sheet_cells
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class PortableValue:
    value: object
    identity: ByteIdentity
    contract: DataContract
    qualifications: frozenset[str] = frozenset()
    coverage: frozenset[str] = frozenset()


def _encode(value, depth=0):
    from . import snapshot_of
    if depth > 64:
        raise ValueError("value.snapshot_depth")
    if value is None or type(value) in {str, bool, int}:
        return ["scalar", value]
    if type(value) is float:
        return ["float", value.hex()]
    if type(value) is Decimal:
        return ["decimal", str(value)]
    if type(value) in {date, datetime, time}:
        return [type(value).__name__, value.isoformat()]
    if type(value) is timedelta:
        return ["timedelta", str((value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds)]
    if type(value) is bytes:
        return ["bytes", base64.b64encode(value).decode("ascii")]
    if isinstance(value, SourcePayload):
        return ["source", {"data": base64.b64encode(value.data).decode("ascii"),
            "media_type": value.media_type, "source_id": value.source_id, "charset": value.charset}]
    if isinstance(value, Representation):
        return ["representation", {"profile_id": value.profile_id, "version": value.version,
            "media_type": value.media_type, "encoding": value.encoding,
            "data": base64.b64encode(value.data).decode("ascii")}]
    if isinstance(value, WorkbookCells):
        for sheet in value.sheets:
            validate_sheet_cells(sheet)
        return ["workbook-cells", {"source_identity": identity_value(value.identity), "sheets": [
            {"name": sheet.name, "index": sheet.index, "rows": sheet.rows, "columns": sheet.columns,
             "merged_ranges": list(sheet.merged_ranges), "cells": [[cell.row, cell.column, cell.coordinate,
                 _encode(cell.value, depth + 1), cell.raw_token, cell.kind, cell.formula,
                 cell.number_format, cell.indent, [list(pair) for pair in cell.formula_attributes], cell.evidence_kind]
                 for cell in sheet.cells]} for sheet in value.sheets]}]
    if isinstance(value, TypedTable):
        return ["table", loads(encode_table(value))]
    snapshot = snapshot_of(value)
    if snapshot is not None:
        kind = {"WorkbookExtract": "workbook", "DocumentExtract": "document",
                "ObservationBatch": "observations", "ObservationView": "view"}.get(type(value).__name__, "snapshot")
        if kind == "snapshot" and not isinstance(value, DatasetSnapshot):
            raise ValueError("value.snapshot_type_unsupported")
        return [kind, {"manifest": manifest_value(snapshot.manifest),
            "tables": [[name, loads(encode_table(table))] for name, table in snapshot.tables]}]
    if isinstance(value, Mapping) and all(type(name) is str for name in value):
        return ["mapping", {name: _encode(item, depth + 1) for name, item in value.items()}]
    if type(value) in {tuple, list}:
        return [type(value).__name__, [_encode(item, depth + 1) for item in value]]
    raise ValueError("value.snapshot_type_unsupported")


def _decode(value, max_bytes, max_cells, depth=0, budget=None):
    if budget is None:
        budget = [max_cells]
    if depth > 64 or not isinstance(value, list) or len(value) != 2:
        raise ValueError("value.snapshot_encoding_invalid")
    kind, data = value
    if kind == "scalar" and (data is None or type(data) in {str, bool, int}):
        return data
    if kind == "float" and isinstance(data, str):
        return float.fromhex(data)
    if kind == "decimal" and isinstance(data, str):
        return Decimal(data)
    if kind in {"date", "datetime", "time"} and isinstance(data, str):
        return {"date": date, "datetime": datetime, "time": time}[kind].fromisoformat(data)
    if kind == "timedelta" and isinstance(data, str):
        return timedelta(microseconds=int(data))
    if kind == "bytes" and isinstance(data, str):
        return base64.b64decode(data, validate=True)
    if kind == "source" and isinstance(data, dict) and set(data) == {"data", "media_type", "source_id", "charset"}:
        return SourcePayload(base64.b64decode(data["data"], validate=True), data["media_type"],
            data["source_id"], charset=data["charset"])
    if kind == "representation" and isinstance(data, dict) and set(data) == {"profile_id", "version", "media_type", "encoding", "data"}:
        return Representation(data["profile_id"], data["version"], data["media_type"],
            base64.b64decode(data["data"], validate=True), data["encoding"])
    if kind == "workbook-cells":
        if not isinstance(data, dict) or set(data) != {"source_identity", "sheets"} or not isinstance(data["sheets"], list):
            raise ValueError("value.snapshot_encoding_invalid")
        sheets = []
        for sheet in data["sheets"]:
            if not isinstance(sheet, dict) or set(sheet) != {"name", "index", "rows", "columns", "merged_ranges", "cells"}:
                raise ValueError("value.snapshot_encoding_invalid")
            if not isinstance(sheet["cells"], list) or len(sheet["cells"]) > budget[0]:
                raise ValueError("dataset.cell_limit")
            budget[0] -= len(sheet["cells"])
            cells = []
            for cell in sheet["cells"]:
                if not isinstance(cell, list) or len(cell) != 11:
                    raise ValueError("value.snapshot_encoding_invalid")
                cells.append(WorkbookCell(*cell[:3], _decode(cell[3], max_bytes, max_cells, depth + 1, budget),
                    *cell[4:9], tuple(tuple(pair) for pair in cell[9]), cell[10]))
            result = SheetCells(sheet["name"], sheet["index"], sheet["rows"], sheet["columns"], tuple(cells), tuple(sheet["merged_ranges"]))
            validate_sheet_cells(result)
            sheets.append(result)
        if (tuple(sheet.index for sheet in sheets) != tuple(range(len(sheets)))
                or len({sheet.name for sheet in sheets}) != len(sheets)):
            raise ValueError("value.snapshot_encoding_invalid")
        return WorkbookCells(tuple(sheets), identity_from(data["source_identity"]))
    if kind == "table":
        table = decode_table(_dump(data, max_bytes), max_bytes=max_bytes, max_cells=budget[0])
        budget[0] -= len(table.rows) * max(1, len(table.schema.columns))
        return table
    if kind in {"snapshot", "workbook", "document", "observations", "view"}:
        if not isinstance(data, dict) or set(data) != {"manifest", "tables"} or not isinstance(data["tables"], list):
            raise ValueError("value.snapshot_encoding_invalid")
        tables = []
        for item in data["tables"]:
            if not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str):
                raise ValueError("value.snapshot_encoding_invalid")
            table = decode_table(_dump(item[1], max_bytes), max_bytes=max_bytes, max_cells=budget[0])
            budget[0] -= len(table.rows) * max(1, len(table.schema.columns))
            tables.append((item[0], table))
        snapshot = DatasetSnapshot(manifest_from(data["manifest"]), tuple(tables))
        if kind == "snapshot":
            return snapshot
        if kind == "workbook":
            from stratbox.shared.data.workbooks import workbook_from_snapshot
            return workbook_from_snapshot(snapshot)
        if kind == "document":
            from stratbox.shared.data.documents import document_from_snapshot
            return document_from_snapshot(snapshot)
        if kind == "observations":
            from stratbox.shared.data.observation_snapshots import observations_from_snapshot
            return observations_from_snapshot(snapshot)
        from stratbox.shared.data.views import view_from_snapshot
        return view_from_snapshot(snapshot)
    if kind == "mapping" and isinstance(data, dict):
        return {name: _decode(item, max_bytes, max_cells, depth + 1, budget) for name, item in data.items()}
    if kind in {"tuple", "list"} and isinstance(data, list):
        items = [_decode(item, max_bytes, max_cells, depth + 1, budget) for item in data]
        return tuple(items) if kind == "tuple" else items
    raise ValueError("value.snapshot_encoding_invalid")


def _dump(value, max_bytes):
    if type(max_bytes) is not int or max_bytes < 0:
        raise ValueError("value.snapshot_limit_invalid")
    chunks, size = [], 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    for chunk in encoder.iterencode(value):
        data = chunk.encode("utf-8")
        size += len(data)
        if size > max_bytes:
            raise ValueError("value.snapshot_limit")
        chunks.append(data)
    return b"".join(chunks)


def encode_value(value, contract, *, qualifications=frozenset(), coverage=frozenset(), max_bytes=64 * 1024 * 1024):
    if not isinstance(contract, DataContract):
        raise ValueError("value.snapshot_contract_required")
    if any(not isinstance(items, frozenset) or any(not isinstance(item, str) or not item for item in items)
           for items in (qualifications, coverage)):
        raise ValueError("value.snapshot_qualification_invalid")
    return _dump({"encoding": "stratbox.accepted-value.v1", "contract": contract_value(contract),
        "qualifications": sorted(qualifications), "coverage": sorted(coverage),
        "identity": identity_value(_logical_identity(value)), "value": _encode(value)}, max_bytes)


def decode_value(data, *, max_bytes=64 * 1024 * 1024, max_cells=5_000_000):
    if type(max_cells) is not int or max_cells < 0:
        raise ValueError("value.snapshot_limit_invalid")
    raw = loads(data, max_bytes=max_bytes)
    if not isinstance(raw, dict) or set(raw) != {"encoding", "contract", "qualifications", "coverage", "identity", "value"}:
        raise ValueError("value.snapshot_encoding_invalid")
    if raw["encoding"] != "stratbox.accepted-value.v1":
        raise ValueError("value.snapshot_version_unsupported")
    if any(not isinstance(raw[name], list) or any(not isinstance(item, str) or not item for item in raw[name])
           or len(raw[name]) != len(set(raw[name]))
           for name in ("qualifications", "coverage")):
        raise ValueError("value.snapshot_encoding_invalid")
    value = _decode(raw["value"], max_bytes, max_cells)
    identity = identity_from(raw["identity"])
    if _logical_identity(value) != identity:
        raise ValueError("value.snapshot_identity_mismatch")
    return PortableValue(value, identity, contract_from(raw["contract"]),
        frozenset(raw["qualifications"]), frozenset(raw["coverage"]))


def _logical_identity(value):
    from . import value_identity, argument_identity
    # A decoded workbook carries its original byte identity; a representation
    # carries an encoding identity. Their portable logical values also include
    # the cells/profile/source semantics and need a separate content seal.
    return argument_identity(value) if isinstance(value, (WorkbookCells, Representation, SourcePayload)) else value_identity(value)
