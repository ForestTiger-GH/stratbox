"""Strict explicit alignment; publication history preserves each supplied edition."""
from dataclasses import replace
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.evidence import UsedInputReceipt
from ..tables.snapshots import validate_flake, flake_snapshot


def _receipt(batch):
    return UsedInputReceipt("integrated_release", observation_snapshot(batch).identity,
                            "application/vnd.stratbox.dataset+json", "inline", batch.dataset_id)


def _key(item):
    return item.subject, item.metric, item.period, tuple(sorted(item.dimensions)), item.perimeter


def _batch(dataset_id, release_id, rows, lineage, source_uses):
    value = ObservationBatch(dataset_id, 1, release_id, tuple(rows), tuple(dict.fromkeys(lineage)), source_uses)
    observation_snapshot(value)
    return value


def integrate(request):
    validate_flake(request.flake)
    flake = request.flake
    return _batch(request.dataset_id, request.release_id, flake.batch.observations,
        (*flake.batch.lineage, UsedInputReceipt("semantic_flake", flake_snapshot(flake).identity,
            "application/vnd.stratbox.dataset+json", "inline", flake.series_id)), flake.batch.source_uses)


def align(request):
    if not isinstance(request.batches, tuple) or not request.batches:
        raise ValueError("frg.integration.batches_required")
    rows, lineage, keys, metrics = [], [], set(), {}
    for batch in request.batches:
        lineage.extend((*batch.lineage, _receipt(batch)))
        for item in batch.observations:
            if item.metric.id in metrics and metrics[item.metric.id] != item.metric:
                raise ValueError("frg.integration.metric_definition_mismatch")
            metrics[item.metric.id] = item.metric
            key = _key(item)
            if key in keys:
                raise ValueError("frg.integration.duplicate_semantic_key")
            keys.add(key)
            rows.append(item)
    return _batch(request.dataset_id, request.release_id, rows, lineage,
        tuple(use for batch in request.batches for use in batch.source_uses))


def history(request):
    if not isinstance(request.batches, tuple) or not request.batches:
        raise ValueError("frg.history.batches_required")
    identities, rows, lineage = set(), [], []
    for batch in request.batches:
        key = batch.dataset_id, batch.release_id
        if key in identities:
            raise ValueError("frg.history.duplicate_release")
        identities.add(key)
        lineage.extend((*batch.lineage, _receipt(batch)))
        for item in batch.observations:
            if {"publication_release", "publication_dataset"} & dict(item.dimensions).keys():
                raise ValueError("frg.history.already_versioned")
            rows.append(replace(item, dimensions=(*item.dimensions,
                ("publication_dataset", batch.dataset_id), ("publication_release", batch.release_id))))
    return _batch(request.dataset_id, request.release_id, rows, lineage,
        tuple(use for batch in request.batches for use in batch.source_uses))
