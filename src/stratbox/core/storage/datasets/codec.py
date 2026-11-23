"""Bounded, explicit JSON codecs for portable tables and snapshot manifests."""

from __future__ import annotations

import base64
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import struct

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import (
    ColumnSchema, ComponentLink, DatasetAssembly, DatasetManifest, ScalarType, SnapshotCoverage,
    SnapshotReference, TableComponent, TableSchema, TypedTable, identity_value, manifest_value, scalar_value, table_value,
)
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

TABLE_MEDIA_TYPE = "application/vnd.stratbox.typed-table+json"
SNAPSHOT_MEDIA_TYPE = "application/vnd.stratbox.dataset+json"


def _object(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("dataset.encoding_invalid")
    return value


def _list(value):
    if not isinstance(value, list):
        raise ValueError("dataset.encoding_invalid")
    return value


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("dataset.duplicate_json_key")
        value[key] = item
    return value


def loads(data: bytes, *, max_bytes: int = 64 * 1024 * 1024):
    if type(data) is not bytes or len(data) > max_bytes:
        raise ValueError("dataset.encoding_limit")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("dataset.encoding_invalid")))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("dataset.encoding_invalid") from error


def identity_from(value) -> ByteIdentity:
    value = _object(value, ("sha256", "size"))
    if type(value["sha256"]) is not str or type(value["size"]) is not int:
        raise ValueError("dataset.encoding_invalid")
    return ByteIdentity(value["sha256"], value["size"])


def contract_from(value) -> DataContract:
    value = _object(value, ("schema_id", "version", "role"))
    return DataContract(value["schema_id"], value["version"], DataRole(value["role"]) if value["role"] is not None else None)


def schema_from(value) -> TableSchema:
    value = _object(value, ("encoding", "contract", "columns", "primary_key"))
    if value["encoding"] != "stratbox.table-schema.v1":
        raise ValueError("dataset.schema_version_unsupported")
    columns = []
    for c in _list(value["columns"]):
        c = _object(c, ("name", "type", "nullable", "unit"))
        columns.append(ColumnSchema(c["name"], ScalarType(c["type"]), c["nullable"], c["unit"]))
    return TableSchema(contract_from(value["contract"]), tuple(columns), tuple(_list(value["primary_key"])))


def _scalar_from(value, column):
    if value is None:
        result = None
    else:
        kind = column.scalar_type
        if kind is ScalarType.BOOLEAN:
            result = value
        elif kind in {ScalarType.INT64, ScalarType.INTEGER}:
            result = int(value) if type(value) is str else value
        elif kind is ScalarType.FLOAT64:
            if not isinstance(value, str) or len(value) != 16:
                raise ValueError("dataset.encoding_invalid")
            result = struct.unpack(">d", bytes.fromhex(value))[0]
        elif kind is ScalarType.DECIMAL:
            result = Decimal(value) if type(value) is str else value
        elif kind is ScalarType.TEXT:
            result = value
        elif kind is ScalarType.BINARY:
            result = base64.b64decode(value, validate=True) if type(value) is str else value
        elif kind is ScalarType.DATE:
            result = date.fromisoformat(value)
        elif kind in {ScalarType.TIMESTAMP, ScalarType.LOCAL_DATETIME}:
            result = datetime.fromisoformat(value)
        elif kind is ScalarType.DURATION:
            result = timedelta(microseconds=int(value)) if type(value) is str else value
        else:
            raise ValueError("dataset.scalar_type_unsupported")
    # Canonical round-trip rejects permissive casts, noncanonical encodings and
    # booleans supplied as numeric JSON values.
    if scalar_value(result, column) != value:
        raise ValueError("dataset.encoding_noncanonical")
    return result


def encode_table(table: TypedTable) -> bytes:
    value = table_value(table)
    value["encoding"] = "stratbox.typed-table.json.v1"
    value["logical_identity"] = identity_value(table.identity)
    return canonical_manifest_bytes(value)


def decode_table(data: bytes, *, expected_identity: ByteIdentity | None = None,
                 max_bytes: int = 64 * 1024 * 1024, max_cells: int = 5_000_000) -> TypedTable:
    value = _object(loads(data, max_bytes=max_bytes), ("encoding", "schema", "rows", "logical_identity"))
    if value["encoding"] != "stratbox.typed-table.json.v1":
        raise ValueError("dataset.table_codec_unsupported")
    schema = schema_from(value["schema"])
    rows = _list(value["rows"])
    if type(max_cells) is not int or max_cells < 0 or len(rows) * max(1, len(schema.columns)) > max_cells:
        raise ValueError("dataset.cell_limit")
    if any(not isinstance(row, list) or len(row) != len(schema.columns) for row in rows):
        raise ValueError("dataset.row_width_mismatch")
    table = TypedTable(schema, tuple(tuple(_scalar_from(item, column) for item, column in zip(row, schema.columns)) for row in rows))
    if table.identity != identity_from(value["logical_identity"]) or (expected_identity is not None and table.identity != expected_identity):
        raise ValueError("dataset.component_mismatch")
    return table


def _input_from(value):
    value = _object(value, ("role", "identity", "media_type", "availability", "source_id", "container", "member", "version"))
    return UsedInputReceipt(value["role"], identity_from(value["identity"]), value["media_type"], value["availability"],
                            value["source_id"], identity_from(value["container"]) if value["container"] is not None else None,
                            value["member"], identity_from(value["version"]) if value["version"] is not None else None)


def manifest_from(value) -> DatasetManifest:
    value = _object(value, ("encoding", "dataset_id", "version_id", "contract", "components", "coverage", "inputs", "parents"))
    if value["encoding"] != "stratbox.dataset.logical.v1":
        raise ValueError("dataset.manifest_codec_unsupported")
    components = []
    for c in _list(value["components"]):
        c = _object(c, ("name", "schema", "identity", "row_count"))
        components.append(TableComponent(c["name"], schema_from(c["schema"]), identity_from(c["identity"]), c["row_count"]))
    from stratbox.shared.data.snapshots import coverage_from
    coverage = coverage_from(value["coverage"])
    return DatasetManifest(value["dataset_id"], value["version_id"], contract_from(value["contract"]), tuple(components),
                           coverage,
                           tuple(_input_from(i) for i in _list(value["inputs"])),
                           tuple(identity_from(i) for i in _list(value["parents"])))


def reference_value(reference: SnapshotReference) -> dict:
    return {"provider_id": reference.provider_id, "scope_id": reference.scope_id,
            "dataset_id": reference.dataset_id, "version_id": reference.version_id,
            "identity": identity_value(reference.identity)}


def reference_from(value) -> SnapshotReference:
    value = _object(value, ("provider_id", "scope_id", "dataset_id", "version_id", "identity"))
    return SnapshotReference(value["provider_id"], value["scope_id"], value["dataset_id"], value["version_id"], identity_from(value["identity"]))


def encode_assembly(assembly: DatasetAssembly) -> bytes:
    return canonical_manifest_bytes({"encoding": "stratbox.dataset-assembly.json.v1",
        "manifest": manifest_value(assembly.manifest),
        "links": [{"name": link.name, "snapshot": reference_value(link.snapshot), "component": link.component} for link in assembly.links]})


def decode_assembly(data: bytes) -> DatasetAssembly:
    value = _object(loads(data), ("encoding", "manifest", "links"))
    if value["encoding"] != "stratbox.dataset-assembly.json.v1":
        raise ValueError("dataset.assembly_codec_unsupported")
    links = []
    for item in _list(value["links"]):
        item = _object(item, ("name", "snapshot", "component"))
        links.append(ComponentLink(item["name"], reference_from(item["snapshot"]), item["component"]))
    return DatasetAssembly(manifest_from(value["manifest"]), tuple(links))
