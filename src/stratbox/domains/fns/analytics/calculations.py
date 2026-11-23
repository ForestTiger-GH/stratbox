"""Explicit stock changes and shares; a change in population is never an entry flow."""
from dataclasses import dataclass, replace
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from stratbox.shared.data.observations import MetricRef, ObservationBatch, PeriodRef
from stratbox.shared.data.calculations import exact_difference
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from ..integration.contracts import FnsDataset
from ..tables.snapshots import admitted_snapshot_contract, layer_snapshot, read_layer, snapshot_contract

_PROVENANCE_DIMENSIONS = frozenset({"source_field", "source_indicator", "source_legal_kind"})


@dataclass(frozen=True, slots=True)
class Calculation(FnsDataset):
    @property
    def identity(self):
        return calculation_snapshot(self).identity


def calculation_snapshot(value, *, dataset_id=None, version_id=None):
    if not isinstance(value, Calculation) or value.source_identity not in value.parents:
        raise ValueError("fns.calculation_invalid")
    return layer_snapshot(value, snapshot_contract(value.context.series_id, "calculation"),
                          dataset_id=dataset_id, version_id=version_id, parents=value.parents)


def calculation_from_snapshot(snapshot):
    value = Calculation(*read_layer(snapshot, admitted_snapshot_contract(snapshot, "calculation")), snapshot.manifest.parents)
    if calculation_snapshot(value, dataset_id=snapshot.manifest.dataset_id,
                            version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("fns.calculation_snapshot_identity_mismatch")
    return value


def _receipt(value, role):
    return UsedInputReceipt(role, value.identity, "application/vnd.stratbox.dataset+json",
                            "reference_only", value.batch.dataset_id)


def _key(item, *, exclude=(), include_metric=True):
    ignored = _PROVENANCE_DIMENSIONS | set(exclude)
    return (item.subject, item.metric if include_metric else (item.metric.unit, item.metric.quantity_kind,
        item.metric.definition_version, item.metric.scale), item.perimeter,
        tuple(sorted((key, value) for key, value in item.dimensions if key not in ignored)))


def _index(items, key):
    result = {}
    for item in items:
        identity = key(item)
        if identity in result:
            raise ValueError("fns.calculation.ambiguous_observation")
        result[identity] = item
    if not result:
        raise ValueError("fns.calculation.empty_selection")
    return result


def _numeric_stock(item):
    if (item.metric.quantity_kind != "stock" or not item.metric.definition_version
            or item.metric.scale is None
            or item.period.kind != "as_of" or type(item.value) not in {int, Decimal}
            or item.value_status != "reported"):
        raise ValueError("fns.calculation.reported_stock_required")


def net_changes(before, after, *, metric_ids=()):
    if (before.context.series_id != after.context.series_id or before.profile_id != after.profile_id
            or before.context.observation_date >= after.context.observation_date):
        raise ValueError("fns.calculation.source_or_period_mismatch")
    selected = set(metric_ids) or {item.metric.id for item in after.batch.observations
                                  if item.metric.quantity_kind == "stock"}
    left = _index((item for item in before.batch.observations if item.metric.id in selected), _key)
    right = _index((item for item in after.batch.observations if item.metric.id in selected), _key)
    if set(left) != set(right) or {item.metric.id for item in right.values()} != selected:
        raise ValueError("fns.calculation.coverage_mismatch")
    observations = []
    before_identity, after_identity = before.identity, after.identity
    method = "fns.stock-net-change.v1"
    for key, current in right.items():
        previous = left[key]
        _numeric_stock(previous)
        _numeric_stock(current)
        if (previous.period.as_of != before.context.observation_date or
                current.period.as_of != after.context.observation_date):
            raise ValueError("fns.calculation.observation_date_mismatch")
        observations.append(replace(current,
            metric=MetricRef(current.metric.id + ".net_change", current.metric.unit, "count", method, current.metric.scale),
            period=PeriodRef("interval", start=previous.period.as_of, end=current.period.as_of),
            value=exact_difference(previous.value, current.value), value_status="derived", raw_token=None,
            evidence_ref=f"before:{before_identity.sha256}:{previous.evidence_ref}|after:{after_identity.sha256}:{current.evidence_ref}"))
    lineage = (*before.batch.lineage, *after.batch.lineage, _receipt(before, "before_dataset"), _receipt(after, "after_dataset"))
    # Preserve source receipt order while removing exact duplicates shared by both editions.
    lineage = tuple(dict.fromkeys(lineage))
    batch = ObservationBatch(after.context.series_id + ".net_changes", 1,
        "change-" + ByteIdentity.of(canonical_manifest_bytes({"before": before_identity.sha256,
            "after": after_identity.sha256, "metrics": sorted(selected)})).sha256,
        tuple(observations), lineage, tuple(replace(use, input_role=role) for role, source in
            (("before", before), ("after", after)) for use in source.batch.source_uses))
    return Calculation(after.context, after_identity, batch, method,
        SnapshotCoverage("partial", "Exactly the matched selected stock observations and their two source vintages."),
        tuple(dict.fromkeys((*before.qualifications, *after.qualifications,
            "calculation.net_stock_change_is_not_entries_or_exits"))), (),
        canonical_manifest_bytes({"method": method, "metrics": sorted(selected),
            "before_dataset": before_identity.sha256, "after_dataset": after_identity.sha256}).decode("utf-8"),
        (before_identity, after_identity))


def shares(dataset, *, numerator_metric, denominator_metric, numerator_dimensions=(), denominator_dimensions=()):
    def selected(metric, dimensions):
        required = dict(dimensions)
        return tuple(item for item in dataset.batch.observations if item.metric.id == metric
            and all(dict(item.dimensions).get(key) == value for key, value in required.items()))
    excluded = {key for key, _ in (*numerator_dimensions, *denominator_dimensions)}
    key = lambda item: (_key(item, exclude=excluded, include_metric=False), item.period)
    numerators = _index(selected(numerator_metric, numerator_dimensions), key)
    denominators = _index(selected(denominator_metric, denominator_dimensions), key)
    if set(numerators) != set(denominators):
        raise ValueError("fns.calculation.coverage_mismatch")
    observations, qualifications = [], list(dataset.qualifications)
    dataset_identity = dataset.identity
    method = "fns.reported-stock-share.v1"
    for identity, numerator in numerators.items():
        denominator = denominators[identity]
        _numeric_stock(numerator)
        _numeric_stock(denominator)
        if numerator.value < 0 or denominator.value < 0:
            raise ValueError("fns.calculation.nonnegative_stock_required")
        if denominator.value == 0:
            value, status = None, "missing"
            qualifications.append("calculation.zero_denominator")
        else:
            with localcontext(Context(prec=36, rounding=ROUND_HALF_EVEN)):
                value = Decimal(numerator.value) / Decimal(denominator.value)
            status = "derived"
        observations.append(replace(numerator,
            metric=MetricRef(numerator_metric + ".share", "ratio", "ratio", method, Decimal(1)),
            value=value, value_status=status, raw_token=None,
            dimensions=(*numerator.dimensions, ("denominator_metric", denominator_metric),
                ("denominator_selection", canonical_manifest_bytes({"dimensions": denominator_dimensions}).decode("utf-8"))),
            evidence_ref=f"numerator:{numerator.evidence_ref}|denominator:{denominator.evidence_ref}|dataset:{dataset_identity.sha256}"))
    lineage = (*dataset.batch.lineage, _receipt(dataset, "input_dataset"))
    parameters = {"numerator_metric": numerator_metric, "denominator_metric": denominator_metric,
        "numerator_dimensions": numerator_dimensions, "denominator_dimensions": denominator_dimensions,
        "dataset": dataset_identity.sha256, "precision": 36}
    batch = ObservationBatch(dataset.context.series_id + ".shares", 1,
        "share-" + ByteIdentity.of(canonical_manifest_bytes(parameters)).sha256, tuple(observations), lineage, dataset.batch.source_uses)
    return Calculation(dataset.context, dataset_identity, batch, method,
        SnapshotCoverage("partial", "Explicit numerator/denominator selections at identical periods, subjects, perimeters and editions."),
        tuple(dict.fromkeys(qualifications)), (), canonical_manifest_bytes(parameters).decode("utf-8"), (dataset_identity,))
