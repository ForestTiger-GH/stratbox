"""Complete escrow interchange through typed logical dataset snapshots.

Physical storage is chosen by the caller. Decoders require every component and
validate domain structure before reconstructing a value for subsequent work.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
import json

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .contracts import EscrowIndicatorSpec
T, I, D, B = ScalarType.TEXT, ScalarType.INT64, ScalarType.DECIMAL, ScalarType.BOOLEAN

def _schema(name, fields, *, role=DataRole.EXTRACTS, key=()):
    return TableSchema(DataContract(f"cbr.escrow.{name}", 1, role),
                       tuple(ColumnSchema(n, t, nullable) for n, t, nullable in fields), key)


SPECS = _schema("indicators", (("indicator_code", T, False), ("specification", T, False)), key=("indicator_code",))

def _json(value):
    return canonical_manifest_bytes(value).decode("utf-8")


def _string_tuple(value):
    result = json.loads(value)
    if not isinstance(result, list) or any(type(item) is not str for item in result):
        raise ValueError("escrow.snapshot_text_list_invalid")
    return tuple(result)


def _specs(values):
    return TypedTable(SPECS, tuple((spec.code, _json(asdict(spec))) for spec in values))


def _frame(table):
    import pandas as pd
    return pd.DataFrame(list(table.rows), columns=[column.name for column in table.schema.columns], dtype=object)


def frame_table(frame, schema):
    if tuple(frame.columns) != tuple(column.name for column in schema.columns):
        raise ValueError("escrow.snapshot_columns_invalid")
    return TypedTable(schema, tuple(tuple(row) for row in frame.itertuples(index=False, name=None)))


def _check(snapshot, contract, components):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != contract
            or tuple(name for name, _ in snapshot.tables) != tuple(components)):
        raise ValueError("escrow.snapshot_invalid")
    for name, schema in components.items():
        if snapshot.table(name).schema != schema:
            raise ValueError("escrow.snapshot_schema_invalid")


def _check_lineage(snapshot, expected):
    observed = tuple(replace(item, availability="reference_only") for item in snapshot.manifest.inputs)
    if observed != expected or snapshot.manifest.parents:
        raise ValueError("escrow.snapshot_lineage_mismatch")


def _build(dataset_id, version_id, contract, tables, *, coverage, inputs=()):
    version = version_id or ByteIdentity.of(canonical_manifest_bytes(
        {"contract": contract.schema_id, "coverage": asdict(coverage),
         "tables": [[name, table.identity.sha256, table.identity.size] for name, table in tables],
         "inputs": [[item.role, item.identity.sha256, item.identity.size, item.source_id] for item in inputs]}
    )).sha256
    return DatasetSnapshot.build(dataset_id, version, contract, tables, coverage=coverage, inputs=inputs)


def _read_specs(table):
    if table.schema != SPECS:
        raise ValueError("escrow.snapshot_schema_invalid")
    output = []
    for code, payload in table.rows:
        fields = json.loads(payload)
        if not isinstance(fields, dict):
            raise ValueError("escrow.snapshot_indicators_invalid")
        item = EscrowIndicatorSpec(**fields)
        if item.code != code:
            raise ValueError("escrow.snapshot_indicators_invalid")
        output.append(item)
    return tuple(output)
