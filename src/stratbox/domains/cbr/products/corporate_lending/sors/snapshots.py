"""Data-only snapshots for fully prepared SORS product tables."""
from __future__ import annotations

from dataclasses import asdict
import json
import re

from stratbox.core.formats.dataframes import frame_from_table, frame_to_table
from stratbox.shared.data.lineage import computation_from, computation_value
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.data.tables import TABLE_ENCODING, table_identity
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .results import SorsViewPack

CONTRACT = DataContract("cbr.sors.views.snapshot", 1, DataRole.PRODUCTS)
_CONTEXT = TableSchema(DataContract("cbr.sors.views.context", 1, DataRole.PRODUCTS),
                       (ColumnSchema("context", ScalarType.TEXT),))
_FRAME = DataContract("cbr.sors.views.frame", 1, DataRole.PRODUCTS)
_MAX_CONTEXT = 16 * 1024 * 1024


def view_metadata(value):
    return {"profile": value.profile_id,
            "source": asdict(value.source_identity) if value.source_identity else None}


def view_identity(value):
    identity = table_identity(value.tables, allow_infinite=True)
    return ByteIdentity.of(canonical_manifest_bytes({"encoding": TABLE_ENCODING,
        "tables": [identity.sha256, identity.size], "metadata": view_metadata(value)}))


def validate_view_pack(value, *, require_seal=False):
    if not isinstance(value, SorsViewPack) or value.profile_id != "cbr.sors.views.v1" or not value.tables:
        raise ValueError("sors.views_invalid")
    names = [name for name, _ in value.tables]
    if any(
            not isinstance(name, str) or not 1 <= len(name) <= 31 or re.search(r"[:\\/?*\[\]]", name)
            for name in names) or len({name.casefold() for name in names}) != len(names):
        raise ValueError("sors.view_sheet_invalid")
    if require_seal and value.evidence is None:
        raise ValueError("sors.views_unsealed")
    if value.evidence is not None and value.evidence.output != view_identity(value):
        raise ValueError("sors.views_identity_mismatch")


def view_snapshot(value, *, dataset_id="cbr.sors.views", version_id=None, checkpoint=None):
    validate_view_pack(value, require_seal=True)
    tables, descriptors = [], []
    for index, (name, frame) in enumerate(value.tables):
        if checkpoint is not None:
            checkpoint()
        table, descriptor = frame_to_table(frame, contract=_FRAME, checkpoint=checkpoint)
        key = f"sheet_{index}"
        tables.append((key, table))
        descriptors.append({"key": key, "name": name, "descriptor": descriptor})
    body = canonical_manifest_bytes({**view_metadata(value), "sheets": descriptors,
                                     "evidence": computation_value(value.evidence)})
    if len(body) > _MAX_CONTEXT:
        raise ValueError("sors.views_metadata_limit")
    return DatasetSnapshot.build(dataset_id, version_id or value.evidence.output.sha256, CONTRACT,
        (("context", TypedTable(_CONTEXT, ((body.decode("utf-8"),),))), *tables),
        coverage=SnapshotCoverage("complete", "Every selected prepared product sheet is retained."),
        inputs=value.evidence.inputs)


def view_from_snapshot(snapshot, *, checkpoint=None):
    if not isinstance(snapshot, DatasetSnapshot) or snapshot.manifest.contract != CONTRACT or not snapshot.complete:
        raise ValueError("sors.views_snapshot_contract_invalid")
    context = snapshot.table("context")
    if context.schema != _CONTEXT or len(context.rows) != 1:
        raise ValueError("sors.views_snapshot_context_invalid")
    raw = context.rows[0][0].encode("utf-8")
    if len(raw) > _MAX_CONTEXT:
        raise ValueError("sors.views_metadata_limit")
    data = json.loads(raw)
    if (canonical_manifest_bytes(data) != raw or set(data) != {"profile", "source", "sheets", "evidence"}
            or not isinstance(data["sheets"], list)):
        raise ValueError("sors.views_snapshot_context_invalid")
    frames = []
    for index, item in enumerate(data["sheets"]):
        if set(item) != {"key", "name", "descriptor"} or item["key"] != f"sheet_{index}":
            raise ValueError("sors.views_snapshot_sheet_invalid")
        table = snapshot.table(item["key"])
        if table.schema.contract != _FRAME:
            raise ValueError("sors.views_snapshot_sheet_invalid")
        frames.append((item["name"], frame_from_table(table, item["descriptor"], checkpoint=checkpoint)))
    if tuple(name for name, _ in snapshot.tables) != ("context", *(f"sheet_{i}" for i in range(len(frames)))):
        raise ValueError("sors.views_snapshot_members_invalid")
    source = ByteIdentity(**data["source"]) if data["source"] is not None else None
    value = SorsViewPack(tuple(frames), source, data["profile"], computation_from(data["evidence"]))
    validate_view_pack(value, require_seal=True)
    return value
