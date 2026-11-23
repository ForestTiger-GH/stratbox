"""Portable source-local semantic flakes retain all observation qualifications."""
from __future__ import annotations
import json

from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot, OBSERVATION_SNAPSHOT, _COVERAGE
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity
from ..publications.catalog import source
from .contracts import SemanticFlake

FLAKE_SNAPSHOT = DataContract("frg.flake.snapshot", 1, DataRole.EXTRACTS)
_T, _I = ScalarType.TEXT, ScalarType.INTEGER
_META = TableSchema(DataContract("frg.flake.metadata", 1, DataRole.EXTRACTS), tuple(ColumnSchema(k, t) for k, t in (
    ("series_id", _T), ("issue_id", _T), ("asset_id", _T), ("original_sha256", _T), ("original_size", _I),
    ("extract_sha256", _T), ("extract_size", _I), ("profile_id", _T), ("profile_version", _I),
    ("profile_sha256", _T), ("profile_size", _I), ("qualifications", _T))))


def validate_flake(value):
    if not isinstance(value, SemanticFlake):
        raise ValueError("frg.flake.invalid")
    source(value.series_id)
    SourceAssetIdentity(value.series_id, value.issue_id, value.asset_id)
    if not value.issue_id or not value.asset_id or not value.profile_id or type(value.profile_version) is not int or value.profile_version < 1:
        raise ValueError("frg.flake.invalid")
    observation_snapshot(value.batch)
    if any(dict(x.dimensions).get("source_series") != value.series_id or x.metric.scale is None
           or x.metric.definition_version is None or x.metric.quantity_kind is None
           or x.period.kind == "capture" or not x.perimeter
           or x.metric.quantity_kind == "stock" and x.period.kind != "as_of"
           or x.metric.quantity_kind == "flow" and x.period.kind != "interval"
           or not x.evidence_ref.startswith("sha256:" + value.original_identity.sha256 + "#")
           for x in value.batch.observations):
        raise ValueError("frg.flake.evidence_mismatch")
    if any(identity not in {item.identity for item in value.batch.lineage}
           for identity in (value.original_identity, value.extract_identity, value.profile_identity)):
        raise ValueError("frg.flake.lineage_required")


def flake_snapshot(value: SemanticFlake, *, dataset_id=None, version_id=None):
    validate_flake(value)
    observations = observation_snapshot(value.batch)
    meta = ((value.series_id, value.issue_id, value.asset_id, value.original_identity.sha256, value.original_identity.size,
             value.extract_identity.sha256, value.extract_identity.size, value.profile_id, value.profile_version,
             value.profile_identity.sha256, value.profile_identity.size,
             canonical_manifest_bytes({"items": value.qualifications}).decode()),)
    return DatasetSnapshot.build(dataset_id or value.batch.dataset_id, version_id or value.batch.release_id,
        FLAKE_SNAPSHOT, (("source", TypedTable(_META, meta)), *observations.tables),
        coverage=SnapshotCoverage("partial", "Exactly the caller-bound cells; other workbook cells remain in the physical extract."),
        inputs=value.batch.lineage)


def flake_from_snapshot(snapshot: DatasetSnapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != FLAKE_SNAPSHOT
            or tuple(name for name, _ in snapshot.tables) != ("source", "metadata", "observations")
            or snapshot.table("source").schema != _META or len(snapshot.table("source").rows) != 1):
        raise ValueError("frg.flake.snapshot_invalid")
    fields = snapshot.table("source").rows[0]
    batch_snapshot = DatasetSnapshot.build(snapshot.manifest.dataset_id, snapshot.manifest.version_id, OBSERVATION_SNAPSHOT,
        tuple((name, table) for name, table in snapshot.tables if name != "source"),
        coverage=_COVERAGE, inputs=snapshot.manifest.inputs)
    document = json.loads(fields[11])
    if not isinstance(document, dict) or set(document) != {"items"} or not isinstance(document["items"], list) or any(type(x) is not str for x in document["items"]):
        raise ValueError("frg.flake.snapshot_invalid")
    result = SemanticFlake(fields[0], fields[1], fields[2], ByteIdentity(fields[3], fields[4]),
        ByteIdentity(fields[5], fields[6]), fields[7], fields[8], ByteIdentity(fields[9], fields[10]),
        observations_from_snapshot(batch_snapshot), tuple(document["items"]))
    validate_flake(result)
    return result
