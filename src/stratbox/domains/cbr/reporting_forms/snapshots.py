"""Explicit codecs for normalized forms, calculations, views and release history."""

from __future__ import annotations

from datetime import date
from types import MappingProxyType

from stratbox.core.formats.dataframes import frame_from_table, frame_to_table
from stratbox.core.storage.datasets.codec import loads
from stratbox.shared.data.lineage import computation_from, computation_value, input_from, input_value
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.data.tables import TABLE_ENCODING, table_identity
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from .contracts import FormData, FormKey, FormSnapshot, FormViews
from .flakes import validate_key
from .forms.registry import FORM_REGISTRY

RESULT_SNAPSHOT = DataContract("cbr.forms.result.snapshot", 1)
HISTORY = DataContract("cbr.forms.history", 1, DataRole.INTEGRATED)
_METADATA = TableSchema(DataContract("cbr.forms.result.metadata", 1), (
    ColumnSchema("ordinal", ScalarType.INTEGER), ColumnSchema("descriptor", ScalarType.TEXT)), ("ordinal",))


def _spec(value):
    if isinstance(value, FormSnapshot):
        validate_key(value.key)
        return "normalized", (("dbf_rows", value.rows),), {
            "form": value.key.code, "as_of": value.key.as_of, "fields": dict(value.physical_fields)}
    if isinstance(value, FormData):
        return "data", (("long", value.long), ("banks", value.banks), ("model", value.model)), {
            "form": value.form, "indicator_order": dict(value.indicator_order)}
    if isinstance(value, FormViews):
        return "views", tuple(value.sheets.items()), {"form": value.form, "profile": value.profile}
    raise ValueError("cbr.forms.result_type_unsupported")


def validate_result(value):
    kind, frames, metadata = _spec(value)
    if metadata["form"] not in FORM_REGISTRY or not frames:
        raise ValueError("cbr.forms.result_invalid")
    identity = table_identity(frames)
    identity = ByteIdentity.of(canonical_manifest_bytes({
        "encoding": TABLE_ENCODING, "tables": [identity.sha256, identity.size], "metadata": metadata}))
    if value.evidence is not None and identity != value.evidence.output:
        raise ValueError("input.identity_mismatch")
    return kind, frames, metadata


def _encode(value, prefix):
    kind, frames, metadata = validate_result(value)
    components, descriptors = [], []
    for index, (name, frame) in enumerate(frames):
        component = f"{prefix}_frame_{index}"
        table, descriptor = frame_to_table(frame, contract=DataContract(
            "cbr.forms." + kind + ".table", 1, DataRole.PRODUCTS if kind == "views" else DataRole.INTEGRATED))
        components.append((component, table))
        descriptors.append({"component": component, "name": name, "frame": descriptor})
    return {"encoding": "cbr.forms.result.v1", "kind": kind, "metadata": metadata,
        "frames": descriptors, "lineage": [input_value(item) for item in value.lineage],
        "evidence": computation_value(value.evidence)}, tuple(components)


def _decode(descriptor, tables):
    if (not isinstance(descriptor, dict) or set(descriptor) != {
            "encoding", "kind", "metadata", "frames", "lineage", "evidence"}
            or descriptor["encoding"] != "cbr.forms.result.v1"):
        raise ValueError("cbr.forms.result_descriptor_invalid")
    kind, meta = descriptor["kind"], descriptor["metadata"]
    if kind not in {"normalized", "data", "views"} or not isinstance(meta, dict):
        raise ValueError("cbr.forms.result_descriptor_invalid")
    frames, names = [], []
    expected = DataContract("cbr.forms." + kind + ".table", 1,
        DataRole.PRODUCTS if kind == "views" else DataRole.INTEGRATED)
    for item in descriptor["frames"]:
        if not isinstance(item, dict) or set(item) != {"component", "name", "frame"}:
            raise ValueError("cbr.forms.result_descriptor_invalid")
        table = tables.get(item["component"])
        if table is None or table.schema.contract != expected or item["name"] in names:
            raise ValueError("cbr.forms.result_components_invalid")
        names.append(item["name"])
        frames.append(frame_from_table(table, item["frame"]))
    lineage = tuple(input_from(item) for item in descriptor["lineage"])
    evidence = computation_from(descriptor["evidence"])
    if kind == "normalized":
        if set(meta) != {"form", "as_of", "fields"} or names != ["dbf_rows"]:
            raise ValueError("cbr.forms.result_descriptor_invalid")
        value = FormSnapshot(FormKey(meta["form"], date.fromisoformat(meta["as_of"])),
            MappingProxyType(meta["fields"]), frames[0], lineage, evidence)
    elif kind == "data":
        if set(meta) != {"form", "indicator_order"} or names != ["long", "banks", "model"]:
            raise ValueError("cbr.forms.result_descriptor_invalid")
        value = FormData(meta["form"], *frames, MappingProxyType(meta["indicator_order"]), lineage, evidence)
    else:
        if set(meta) != {"form", "profile"}:
            raise ValueError("cbr.forms.result_descriptor_invalid")
        value = FormViews(meta["form"], meta["profile"], MappingProxyType(dict(zip(names, frames))), lineage, evidence)
    validate_result(value)
    return value


def result_snapshot(value, *, dataset_id, version_id):
    descriptor, tables = _encode(value, "result")
    metadata = TypedTable(_METADATA, ((0, canonical_manifest_bytes(descriptor).decode("utf-8")),))
    return DatasetSnapshot.build(dataset_id, version_id, RESULT_SNAPSHOT,
        (("metadata", metadata), *tables),
        coverage=SnapshotCoverage("unknown", "Explicit selected form result; historical publisher coverage is unspecified."),
        inputs=value.lineage)


def _read_descriptors(snapshot, expected):
    if not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != expected:
        raise ValueError("cbr.forms.result_snapshot_invalid")
    table = snapshot.table("metadata")
    if table.schema != _METADATA or not table.rows:
        raise ValueError("cbr.forms.result_snapshot_invalid")
    descriptors, names = [], ["metadata"]
    for ordinal, (position, data) in enumerate(table.rows):
        if position != ordinal:
            raise ValueError("cbr.forms.result_order_invalid")
        descriptor = loads(data.encode("utf-8"))
        descriptors.append(descriptor)
        names.extend(item["component"] for item in descriptor["frames"])
    if tuple(names) != tuple(name for name, _ in snapshot.tables):
        raise ValueError("cbr.forms.result_components_invalid")
    return descriptors


def result_from_snapshot(snapshot):
    descriptors = _read_descriptors(snapshot, RESULT_SNAPSHOT)
    if len(descriptors) != 1:
        raise ValueError("cbr.forms.result_snapshot_invalid")
    result = _decode(descriptors[0], dict(snapshot.tables))
    if result.lineage != snapshot.manifest.inputs:
        raise ValueError("cbr.forms.result_lineage_invalid")
    return result


def integrate_snapshots(values, *, dataset_id, version_id):
    if not values or any(not isinstance(item, FormSnapshot) for item in values):
        raise ValueError("request.snapshots_empty")
    ordered = sorted(values, key=lambda item: item.key.as_of)
    if len({item.key.code for item in ordered}) != 1 or len({item.key.as_of for item in ordered}) != len(ordered):
        raise ValueError("request.duplicate_or_mixed_release")
    rows, tables, lineage = [], [], []
    for index, value in enumerate(ordered):
        descriptor, components = _encode(value, f"release_{index}")
        rows.append((index, canonical_manifest_bytes(descriptor).decode("utf-8")))
        tables.extend(components)
        for item in value.lineage:
            if item not in lineage:
                lineage.append(item)
    return DatasetSnapshot.build(dataset_id, version_id, HISTORY,
        (("metadata", TypedTable(_METADATA, tuple(rows))), *tables),
        coverage=SnapshotCoverage("unknown", "Unique selected form releases; revisions and missing publisher releases are not inferred."),
        inputs=tuple(lineage))


def history_from_snapshot(snapshot):
    values = tuple(_decode(item, dict(snapshot.tables)) for item in _read_descriptors(snapshot, HISTORY))
    if any(not isinstance(item, FormSnapshot) for item in values):
        raise ValueError("cbr.forms.history_invalid")
    rebuilt = integrate_snapshots(values, dataset_id=snapshot.manifest.dataset_id, version_id=snapshot.manifest.version_id)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("cbr.forms.history_identity_mismatch")
    return values


__all__ = ("RESULT_SNAPSHOT", "HISTORY", "result_snapshot", "result_from_snapshot",
           "integrate_snapshots", "history_from_snapshot", "validate_result")
