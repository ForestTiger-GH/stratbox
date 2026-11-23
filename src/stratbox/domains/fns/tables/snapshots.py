"""Portable FNS observation layers with publication context and coverage intact."""
import json
from dataclasses import replace

from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot, OBSERVATION_SNAPSHOT
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from ..publications.contracts import ReleaseContext
from .contracts import FieldDisposition, SourceProjection

def snapshot_contract(series_id, layer):
    if series_id not in {"fns.sme", "fns.1yur"}:
        raise ValueError("fns.source_family_mismatch")
    names = {"flake": "full_json" if series_id == "fns.sme" else "workbook_bundle",
        "projection": "reported_projection", "dataset": "integrated_dataset",
        "calculation": "calculation", "view": "prepared_view"}
    roles = {"flake": DataRole.EXTRACTS, "projection": DataRole.EXTRACTS,
        "dataset": DataRole.INTEGRATED, "calculation": DataRole.PRODUCTS, "view": DataRole.PRODUCTS}
    if layer not in names:
        raise ValueError("fns.snapshot_layer_unknown")
    return DataContract(series_id + "." + names[layer] + ".snapshot", 1, roles[layer])


def admitted_snapshot_contract(snapshot, layer):
    if (not isinstance(snapshot, DatasetSnapshot) or snapshot.manifest.contract not in
            {snapshot_contract(series, layer) for series in ("fns.sme", "fns.1yur")}):
        raise ValueError("fns.snapshot_layer_mismatch")
    return snapshot.manifest.contract


_T, _I, _D, _U = ScalarType.TEXT, ScalarType.INTEGER, ScalarType.DATE, ScalarType.TIMESTAMP
CONTEXT = TableSchema(DataContract("fns.release_context", 1), tuple(ColumnSchema(*spec) for spec in (
    ("series_id", _T), ("issue_id", _T), ("asset_id", _T), ("observation_date", _D),
    ("published_on", _D, True), ("captured_at", _U, True),
    ("source_sha256", _T), ("source_size", _I), ("profile_id", _T),
    ("qualifications", _T), ("dispositions", _T), ("details_json", _T),
)))


def context_table(context, identity, profile_id, qualifications=(), dispositions=(), details_json="{}"):
    json.loads(details_json)
    return TypedTable(CONTEXT, ((context.series_id, context.issue_id, context.asset_id,
        context.observation_date, context.published_on, context.captured_at,
        identity.sha256, identity.size, profile_id,
        canonical_manifest_bytes({"items": qualifications}).decode("utf-8"),
        canonical_manifest_bytes({"items": [
            [item.source_field, item.target_field, item.reason] for item in dispositions
        ]}).decode("utf-8"), details_json),))


def read_context(table):
    if table.schema != CONTEXT or len(table.rows) != 1:
        raise ValueError("fns.context_snapshot_invalid")
    (series, issue, asset, observed, published, captured, sha, size, profile,
     qualifications, dispositions, details) = table.rows[0]
    context = ReleaseContext(series, issue, observed, asset, published, captured)
    qs = json.loads(qualifications)
    ds = json.loads(dispositions)
    if (not isinstance(qs, dict) or set(qs) != {"items"} or not isinstance(qs["items"], list)
            or any(type(item) is not str for item in qs["items"])
            or not isinstance(ds, dict) or set(ds) != {"items"} or not isinstance(ds["items"], list)
            or any(not isinstance(item, list) or len(item) != 3
                   or type(item[0]) is not str or item[1] is not None and type(item[1]) is not str
                   or type(item[2]) is not str for item in ds["items"])):
        raise ValueError("fns.context_snapshot_invalid")
    parsed = (context, ByteIdentity(sha, size), profile, tuple(qs["items"]),
              tuple(FieldDisposition(*item) for item in ds["items"]), details)
    if context_table(*parsed) != table:
        raise ValueError("fns.context_snapshot_noncanonical")
    return parsed


def layer_snapshot(value, contract, *, dataset_id=None, version_id=None, parents=None):
    batch = observation_snapshot(value.batch)
    result = DatasetSnapshot.build(dataset_id or value.batch.dataset_id,
        version_id or "content", contract,
        (("context", context_table(value.context, value.source_identity, value.profile_id,
            value.qualifications, value.dispositions, value.details_json)),
         ("batch_metadata", batch.table("metadata")), ("observations", batch.table("observations"))),
        coverage=value.coverage, inputs=value.batch.lineage,
        parents=parents if parents is not None else (value.source_identity,))
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def read_layer(snapshot, contract):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != contract
            or tuple(name for name, _ in snapshot.tables) != ("context", "batch_metadata", "observations")):
        raise ValueError("fns.observation_layer_snapshot_invalid")
    context, identity, profile, qualifications, dispositions, details = read_context(snapshot.table("context"))
    metadata = snapshot.table("batch_metadata")
    if len(metadata.rows) != 1 or len(metadata.rows[0]) != 4:
        raise ValueError("fns.batch_metadata_invalid")
    dataset_id, _, release_id = metadata.rows[0][:3]
    batch_snapshot = DatasetSnapshot.build(dataset_id, release_id, OBSERVATION_SNAPSHOT,
        (("metadata", snapshot.table("batch_metadata")), ("observations", snapshot.table("observations"))),
        coverage=SnapshotCoverage("unknown", "Exactly the supplied observation batch; source-wide coverage is not inferred."),
        inputs=snapshot.manifest.inputs)
    batch = observations_from_snapshot(batch_snapshot)
    if batch.dataset_id.split(".")[:2] != context.series_id.split("."):
        raise ValueError("fns.observation_context_mismatch")
    return context, identity, batch, profile, snapshot.manifest.coverage, qualifications, dispositions, details


def projection_snapshot(value, *, dataset_id=None, version_id=None):
    if not isinstance(value, SourceProjection):
        raise ValueError("fns.projection_invalid")
    return layer_snapshot(value, snapshot_contract(value.context.series_id, "projection"),
                          dataset_id=dataset_id, version_id=version_id)


def projection_from_snapshot(snapshot):
    value = SourceProjection(*read_layer(snapshot, admitted_snapshot_contract(snapshot, "projection")))
    if projection_snapshot(value, dataset_id=snapshot.manifest.dataset_id,
                           version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("fns.projection_snapshot_identity_mismatch")
    return value
