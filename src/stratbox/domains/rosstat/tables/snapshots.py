"""Portable source flakes: exact scalars, row selection, units and evidence."""
from __future__ import annotations
from dataclasses import fields
import json

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType as S, TableSchema, TypedTable
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .contracts import RosstatSourceFlake, SourceValue, SectionEvidence, RowDecision

FLAKE_CONTRACT = DataContract("rosstat.source_flake", 1, DataRole.EXTRACTS)
# Port metadata for a complete snapshot wrapper; the content manifest stays FLAKE_CONTRACT.
FLAKE_SNAPSHOT_CONTRACT = DataContract("rosstat.source_flake.snapshot", 1, DataRole.EXTRACTS)
_METADATA = TableSchema(DataContract("rosstat.source_flake.metadata", 1, DataRole.EXTRACTS), tuple(ColumnSchema(n,t) for n,t in (
    ("series_id",S.TEXT),("issue_id",S.TEXT),("asset_id",S.TEXT),
    ("source_sha256",S.TEXT),("source_size",S.INTEGER),("physical_sha256",S.TEXT),("physical_size",S.INTEGER),
    ("profile_id",S.TEXT),("profile_version",S.INTEGER),("diagnostics",S.TEXT),
)))
_DATES = {"period_start", "period_end", "display_date"}
_DECIMALS = {"value", "scale"}
_INTS = {"source_row", "source_column"}
_NULLABLE = {"value", "raw_token", "unit", "quantity_kind", "formula"}
_JSON_FIELDS = {"footnotes", "dimensions"}
_VALUES = TableSchema(DataContract("rosstat.source_flake.values",1,DataRole.EXTRACTS),
    (ColumnSchema("ordinal",S.INTEGER),) + tuple(ColumnSchema(f.name,
        S.DATE if f.name in _DATES else S.DECIMAL if f.name in _DECIMALS else S.INTEGER if f.name in _INTS else S.TEXT,
        f.name in _NULLABLE) for f in fields(SourceValue)), ("ordinal",))
_SECTIONS = TableSchema(DataContract("rosstat.source_flake.sections",1,DataRole.EXTRACTS),
    (ColumnSchema("ordinal",S.INTEGER),) + tuple(ColumnSchema(f.name,
        S.INTEGER if f.name in {"title_row","marker_row","start_row","end_row"} else S.TEXT,
        f.name == "marker_row") for f in fields(SectionEvidence)), ("ordinal",))
_DECISIONS = TableSchema(DataContract("rosstat.source_flake.row_decisions",1,DataRole.EXTRACTS),
    (ColumnSchema("ordinal",S.INTEGER),) + tuple(ColumnSchema(f.name,
        S.INTEGER if f.name in {"row","year"} else S.BOOLEAN if f.name == "selected" else S.TEXT)
        for f in fields(RowDecision)), ("ordinal",))


def _json(value):
    return canonical_manifest_bytes({"items":value}).decode("utf-8")


def _items(value, *, pairs=False):
    try:
        decoded=json.loads(value)
        rows=decoded["items"]
        if set(decoded) != {"items"} or type(rows) is not list:
            raise ValueError()
        if pairs:
            if any(type(row) is not list or len(row) != 2 or any(type(x) is not str for x in row) for row in rows):
                raise ValueError()
            rows=[tuple(row) for row in rows]
        elif any(type(row) is not str for row in rows):
            raise ValueError()
        result=tuple(rows)
        if _json(result) != value:
            raise ValueError()
        return result
    except (ValueError,TypeError,KeyError,RecursionError):
        raise ValueError("rosstat.flake_metadata_invalid") from None


def _row(value, json_fields):
    return tuple(_json(getattr(value,f.name)) if f.name in json_fields else getattr(value,f.name) for f in fields(value))


def flake_snapshot(value: RosstatSourceFlake, *, dataset_id=None, version_id=None, checkpoint=None) -> DatasetSnapshot:
    def rows(items, json_fields):
        for index, item in enumerate(items):
            if checkpoint is not None and index % 256 == 0:
                checkpoint()
            yield (index, *_row(item, json_fields))
    metadata=(value.series_id,value.issue_id,value.asset_id,value.source_identity.sha256,value.source_identity.size,
        value.physical_identity.sha256,value.physical_identity.size,value.profile_id,value.profile_version,_json(value.diagnostics))
    tables=(("metadata",TypedTable(_METADATA,(metadata,))),
        ("values",TypedTable(_VALUES,tuple(rows(value.values,_JSON_FIELDS)))),
        ("sections",TypedTable(_SECTIONS,tuple(rows(value.sections,{"headers","notes"})))),
        ("row_decisions",TypedTable(_DECISIONS,tuple(rows(value.row_decisions,set())))))
    return DatasetSnapshot.build(dataset_id or value.series_id + ".flake",
        version_id or value.issue_id + "." + value.source_identity.sha256[:16],FLAKE_CONTRACT,tables,
        coverage=value.coverage,inputs=value.lineage,parents=(value.physical_identity,))


def _restore(table, cls, json_fields):
    result=[]
    for i,row in enumerate(table.rows):
        if row[0] != i:
            raise ValueError("rosstat.flake_order_invalid")
        args={f.name:_items(v,pairs=f.name == "dimensions") if f.name in json_fields else v
              for f,v in zip(fields(cls),row[1:])}
        result.append(cls(**args))
    return tuple(result)


def flake_from_snapshot(snapshot: DatasetSnapshot) -> RosstatSourceFlake:
    expected=(("metadata",_METADATA),("values",_VALUES),("sections",_SECTIONS),("row_decisions",_DECISIONS))
    if (not snapshot.complete or snapshot.manifest.contract != FLAKE_CONTRACT
            or tuple(name for name,_ in snapshot.tables) != tuple(name for name,_ in expected)
            or any(snapshot.table(name).schema != schema for name,schema in expected)
            or len(snapshot.table("metadata").rows) != 1):
        raise ValueError("rosstat.flake_snapshot_invalid")
    series,issue,asset,source_hash,source_size,physical_hash,physical_size,profile,version,diagnostics=snapshot.table("metadata").rows[0]
    value=RosstatSourceFlake(series,issue,asset,ByteIdentity(source_hash,source_size),ByteIdentity(physical_hash,physical_size),
        profile,version,_restore(snapshot.table("values"),SourceValue,_JSON_FIELDS),
        _restore(snapshot.table("sections"),SectionEvidence,{"headers","notes"}),
        _restore(snapshot.table("row_decisions"),RowDecision,set()),snapshot.manifest.inputs,
        snapshot.manifest.coverage,_items(diagnostics))
    rebuilt=flake_snapshot(value,dataset_id=snapshot.manifest.dataset_id,version_id=snapshot.manifest.version_id)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("rosstat.flake_snapshot_identity_mismatch")
    return value
