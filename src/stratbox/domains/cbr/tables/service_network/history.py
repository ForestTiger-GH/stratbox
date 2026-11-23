"""Pin source captures and releases without declaring semantic integration."""
from dataclasses import dataclass
from stratbox.shared.data.releases import ParsedRelease
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.data.lineage import input_value, input_from
from stratbox.shared.identity import canonical_manifest_bytes, ByteIdentity
from stratbox.core.storage.datasets.codec import loads
from .snapshots import release_snapshot, release_from_snapshot

@dataclass(frozen=True, slots=True)
class OfficeHistoryRequest:
    releases: tuple[ParsedRelease, ...]
    dataset_id: str
    version_id: str

CONTRACT = DataContract("cbr.service_network.source_history", 1, DataRole.EXTRACTS)
_META = TableSchema(DataContract("cbr.service_network.source_history.entries", 1, DataRole.EXTRACTS),
    (ColumnSchema("ordinal", ScalarType.INTEGER), ColumnSchema("descriptor", ScalarType.TEXT)), ("ordinal",))


def build_history(request):
    if not request.releases or len({(x.dataset_version.dataset_id, x.as_of) for x in request.releases}) != len(request.releases):
        raise ValueError("request.office_revision_selection_required")
    if len({x.dataset_version.dataset_id for x in request.releases}) != 1:
        raise ValueError("request.office_mixed_source_families")
    rows, tables, inputs = [], [], []
    for index, value in enumerate(sorted(request.releases, key=lambda x: x.as_of)):
        if value.dataset_version.dataset_id not in {"cbr.offices", "cbr.offices_reg"}:
            raise ValueError("source.office_family_unsupported")
        snapshot = release_snapshot(value, dataset=value.dataset_version.dataset_id, profile=value.representation.profile_id,
                                   dataset_id=request.dataset_id, version_id=f"release-{index}")
        descriptor = {"dataset": value.dataset_version.dataset_id, "profile": value.representation.profile_id,
            "snapshot_dataset": snapshot.manifest.dataset_id, "snapshot_version": snapshot.manifest.version_id,
            "coverage": snapshot.manifest.coverage.status, "scope": snapshot.manifest.coverage.description,
            "inputs": [input_value(item) for item in snapshot.manifest.inputs],
            "identity": {"sha256": snapshot.identity.sha256, "size": snapshot.identity.size}}
        rows.append((index, canonical_manifest_bytes(descriptor).decode("utf-8")))
        tables.extend((f"release_{index}_{name}", table) for name, table in snapshot.tables)
        for receipt in value.inputs:
            if receipt not in inputs:
                inputs.append(receipt)
    return DatasetSnapshot.build(request.dataset_id, request.version_id, CONTRACT,
        (("entries", TypedTable(_META, tuple(rows))), *tables),
        coverage=SnapshotCoverage("unknown", "Explicit selected source captures or dated releases; publisher history is not inferred."),
        inputs=tuple(inputs))


def restore_history(snapshot):
    if not snapshot.complete or snapshot.manifest.contract != CONTRACT or snapshot.table("entries").schema != _META:
        raise ValueError("cbr.offices.history_invalid")
    releases, expected = [], ["entries"]
    for index, (ordinal, data) in enumerate(snapshot.table("entries").rows):
        if ordinal != index:
            raise ValueError("cbr.offices.history_order_invalid")
        descriptor = loads(data.encode("utf-8"))
        names = (f"release_{index}_metadata", f"release_{index}_observations")
        expected.extend(names)
        inner = DatasetSnapshot.build(descriptor["snapshot_dataset"], descriptor["snapshot_version"],
            DataContract(descriptor["dataset"] + ".snapshot", 1, DataRole.EXTRACTS),
            tuple((name.rsplit("_", 1)[-1], snapshot.table(name)) for name in names),
            coverage=SnapshotCoverage(descriptor["coverage"], descriptor["scope"]),
            inputs=tuple(input_from(item) for item in descriptor["inputs"]))
        if inner.identity != ByteIdentity(**descriptor["identity"]):
            raise ValueError("cbr.offices.history_identity_mismatch")
        releases.append(release_from_snapshot(inner, dataset=descriptor["dataset"], profile=descriptor["profile"]))
    if tuple(expected) != tuple(name for name, _ in snapshot.tables):
        raise ValueError("cbr.offices.history_components_invalid")
    if build_history(OfficeHistoryRequest(tuple(releases), snapshot.manifest.dataset_id, snapshot.manifest.version_id)).identity != snapshot.identity:
        raise ValueError("cbr.offices.history_identity_mismatch")
    return tuple(releases)
