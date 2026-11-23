"""Retained integrated datasets include context, exact facts, maps and qualifiers."""
from ..tables.snapshots import admitted_snapshot_contract, layer_snapshot, read_layer, snapshot_contract
from .contracts import FnsDataset

def dataset_snapshot(value, *, dataset_id=None, version_id=None):
    if type(value) is not FnsDataset or value.source_identity not in value.parents:
        raise ValueError("fns.dataset_invalid")
    return layer_snapshot(value, snapshot_contract(value.context.series_id, "dataset"),
                          dataset_id=dataset_id, version_id=version_id, parents=value.parents)


def dataset_from_snapshot(snapshot):
    value = FnsDataset(*read_layer(snapshot, admitted_snapshot_contract(snapshot, "dataset")), snapshot.manifest.parents)
    if dataset_snapshot(value, dataset_id=snapshot.manifest.dataset_id,
                        version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("fns.dataset_snapshot_identity_mismatch")
    return value
