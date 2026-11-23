"""Complete integrated statistics, qualifications and exact input-version vector."""
from dataclasses import replace
import json

from stratbox.core.storage.datasets.codec import manifest_from
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import (ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage,
                                           TableSchema, TypedTable, manifest_value)
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.domains.cbr.tables.statistics.contracts import TableDiagnostic
from .contracts import InputVersion, StatisticsDataset

DATASET = DataContract("cbr.statistics.dataset", 1, DataRole.INTEGRATED)
_T, _I = ScalarType.TEXT, ScalarType.INT64
_META = TableSchema(DataContract("cbr.statistics.metadata", 1, DataRole.INTEGRATED), (
    ColumnSchema("mapping_version", _T), ColumnSchema("method", _T), ColumnSchema("batch_count", _I)))
INPUTS = TableSchema(DataContract("cbr.statistics.input_versions", 1), tuple(ColumnSchema(name, kind) for name, kind in (
    ("series_id", _T), ("issue_id", _T), ("original_sha256", _T), ("original_size", _I),
    ("flake_sha256", _T), ("flake_size", _I), ("profile_id", _T), ("profile_version", _I), ("asset_id", _T))))
DIAGNOSTICS = TableSchema(DataContract("cbr.statistics.diagnostics", 1), (
    ColumnSchema("code", _T), ColumnSchema("sheet", _T), ColumnSchema("coordinate", _T, True), ColumnSchema("detail", _T, True)))
_BATCHES = TableSchema(DataContract("cbr.statistics.batches", 1, DataRole.INTEGRATED), (
    ColumnSchema("index", _I), ColumnSchema("manifest", _T)), ("index",))


def input_table(inputs):
    for item in inputs:
        SourceAssetIdentity(item.series_id, item.issue_id, item.asset_id)
    return TypedTable(INPUTS, tuple((item.series_id, item.issue_id, item.original.sha256, item.original.size,
        item.flake.sha256, item.flake.size, item.profile_id, item.profile_version, item.asset_id) for item in inputs))


def inputs_from(table):
    if table.schema != INPUTS:
        raise ValueError("cbr.statistics.inputs_schema_invalid")
    result = tuple(InputVersion(series, issue, ByteIdentity(sha, size), ByteIdentity(fsha, fsize), profile, version, asset)
                   for series, issue, sha, size, fsha, fsize, profile, version, asset in table.rows)
    for item in result:
        SourceAssetIdentity(item.series_id, item.issue_id, item.asset_id)
    return result


def diagnostic_table(items):
    return TypedTable(DIAGNOSTICS, tuple((item.code, item.sheet, item.coordinate, item.detail) for item in items))


def dataset_snapshot(value, *, dataset_id="cbr.statistics", version_id=None):
    if (not isinstance(value, StatisticsDataset) or not value.batches or not value.inputs or not value.mapping_version
            or len({(item.series_id, item.flake) for item in value.inputs}) != len(value.inputs)):
        raise ValueError("cbr.statistics.dataset_invalid")
    sub = tuple(observation_snapshot(batch) for batch in value.batches)
    tables = (("metadata", TypedTable(_META, ((value.mapping_version, value.method, len(sub)),))),
              ("inputs", input_table(value.inputs)), ("diagnostics", diagnostic_table(value.diagnostics)),
              ("batches", TypedTable(_BATCHES, tuple((i, canonical_manifest_bytes(manifest_value(item.manifest)).decode())
                                                    for i, item in enumerate(sub)))))
    tables += tuple((f"batch.{i}.{name}", table) for i, item in enumerate(sub) for name, table in item.tables)
    result = DatasetSnapshot.build(dataset_id, version_id or "content", DATASET, tables,
        coverage=SnapshotCoverage("partial" if value.diagnostics else "unknown",
            "Selected source observations; source identities remain separate unless an explicit mapping binds them."),
        inputs=value.lineage, parents=tuple(item.flake for item in value.inputs))
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def dataset_from_snapshot(snapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != DATASET
            or tuple(name for name, _ in snapshot.tables)[:4] != ("metadata", "inputs", "diagnostics", "batches")):
        raise ValueError("cbr.statistics.snapshot_invalid")
    meta, batch_table, issues = snapshot.table("metadata"), snapshot.table("batches"), snapshot.table("diagnostics")
    if meta.schema != _META or len(meta.rows) != 1 or batch_table.schema != _BATCHES or issues.schema != DIAGNOSTICS:
        raise ValueError("cbr.statistics.snapshot_schema_invalid")
    mapping, method, count = meta.rows[0]
    if count != len(batch_table.rows) or len(snapshot.tables) != 4 + 2 * count:
        raise ValueError("cbr.statistics.snapshot_components_invalid")
    batches = []
    for i, (index, encoded) in enumerate(batch_table.rows):
        if i != index:
            raise ValueError("cbr.statistics.snapshot_order_invalid")
        manifest = manifest_from(json.loads(encoded))
        inner = DatasetSnapshot(manifest, tuple((name, snapshot.table(f"batch.{i}.{name}")) for name in ("metadata", "observations")))
        batches.append(observations_from_snapshot(inner))
    value = StatisticsDataset(tuple(batches), inputs_from(snapshot.table("inputs")), mapping,
        tuple(TableDiagnostic(*row) for row in issues.rows), method)
    rebuilt = dataset_snapshot(value, dataset_id=snapshot.manifest.dataset_id, version_id=snapshot.manifest.version_id)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("cbr.statistics.snapshot_noncanonical")
    return value
