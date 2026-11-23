"""Prepare an explicit view from retained facts; rendering consumes only this value."""
from dataclasses import dataclass, replace

from stratbox.shared.data.views import ObservationView, prepare_observation_view
from stratbox.shared.identity import canonical_manifest_bytes

from ..integration.contracts import FnsDataset
from ..integration.coverage import observation_coverage
from ..tables.snapshots import admitted_snapshot_contract, layer_snapshot, read_layer, snapshot_contract

@dataclass(frozen=True, slots=True)
class PreparedView(FnsDataset):
    @property
    def identity(self):
        return view_snapshot(self).identity

    def observation_view(self):
        return ObservationView(self.profile_id, self.batch, self.source_identity, self.coverage, self.qualifications)


def prepare_view(dataset, *, metric_ids=(), subject_ids=(), period_kinds=(), dimensions=()):
    source_identity = dataset.identity
    profile = dataset.context.series_id + ".observation-view.v1"
    selected = prepare_observation_view(dataset.batch, view_id=profile,
        metric_ids=metric_ids, subject_ids=subject_ids, period_kinds=period_kinds,
        coverage=dataset.coverage, qualifications=dataset.qualifications)
    if (not isinstance(dimensions, tuple) or any(not isinstance(pair, tuple) or len(pair) != 2
            or any(type(item) is not str for item in pair) for pair in dimensions)
            or len(dict(dimensions)) != len(dimensions)):
        raise ValueError("fns.view.dimensions_invalid")
    rows = tuple(item for item in selected.batch.observations
        if all(dict(item.dimensions).get(key) == value for key, value in dimensions))
    coverage = selected.coverage
    if rows != selected.batch.observations:
        coverage = replace(coverage, status="partial", description="Explicit metric, subject, period and dimension selection.")
    coverage = observation_coverage(coverage, rows)
    qualifications = dataset.qualifications + (("view.empty_selection",) if not rows else ())
    batch = replace(selected.batch, observations=rows)
    return PreparedView(dataset.context, source_identity, batch, profile, coverage, qualifications,
        dataset.dispositions, canonical_manifest_bytes({"source_profile": dataset.profile_id,
            "source_details": dataset.details_json, "metric_ids": metric_ids, "subject_ids": subject_ids,
            "period_kinds": period_kinds, "dimensions": dimensions}).decode("utf-8"), (source_identity,))


def view_snapshot(value, *, dataset_id=None, version_id=None):
    if type(value) is not PreparedView or value.parents != (value.source_identity,):
        raise ValueError("fns.view.invalid")
    return layer_snapshot(value, snapshot_contract(value.context.series_id, "view"),
                          dataset_id=dataset_id, version_id=version_id, parents=value.parents)


def view_from_snapshot(snapshot):
    value = PreparedView(*read_layer(snapshot, admitted_snapshot_contract(snapshot, "view")), snapshot.manifest.parents)
    if view_snapshot(value, dataset_id=snapshot.manifest.dataset_id,
                     version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("fns.view.snapshot_identity_mismatch")
    return value
