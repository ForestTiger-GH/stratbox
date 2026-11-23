"""Derived changes and shares retain their complete source-version vector."""
from dataclasses import replace
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.integration.statistics.contracts import StatisticsDataset

_EVIDENCE_DIMENSIONS = frozenset({"source_period_label", "source_value_qualification"})


def _dimensions(item, *, share=False):
    omitted = _EVIDENCE_DIMENSIONS | ({"source_hierarchy"} if share else set())
    return tuple((key, value) for key, value in item.dimensions if key not in omitted)


def _retain_evidence(dimensions, item, prefix):
    for key, value in item.dimensions:
        if key in _EVIDENCE_DIMENSIONS:
            dimensions[prefix + key] = value


def _compute(left, right, method):
    # Absolute differences preserve every input digit. Ratios use a declared,
    # deterministic decimal context independent of the host application's context.
    precision = 28
    if method == "absolute":
        precision = max(precision, max(left.adjusted(), right.adjusted())
                        - min(left.as_tuple().exponent, right.as_tuple().exponent) + 2)
    if precision > 10000:
        raise ValueError("cbr.statistics.calculation_precision_limit")
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        if method == "absolute":
            return right - left
        if method == "growth_percent":
            return (right / left - 1) * 100
        return left / right * 100


def _selected(dataset, release_ids):
    if release_ids and not set(release_ids) <= {batch.release_id for batch in dataset.batches}:
        raise ValueError("cbr.statistics.release_selection_unknown")
    return tuple(item for batch in dataset.batches if not release_ids or batch.release_id in release_ids
                 for item in batch.observations)


def _numeric(item):
    if (item.value_status not in {"reported", "derived", "reconstructed"} or type(item.value) not in {int, Decimal}
            or item.metric.unit in {"source_unspecified", "source_conflicting"} or item.metric.scale is None
            or dict(item.dimensions).get("period_qualification") == "reported_date_interval_unresolved"):
        raise ValueError("cbr.statistics.calculation_input_unqualified")
    return Decimal(item.value)


def _finish(dataset, observations, method, parameters):
    from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
    identity = dataset.identity
    computation = ByteIdentity.of(canonical_manifest_bytes({"method": method,
        "input": identity.sha256, "parameters": parameters}))
    lineage = (*dataset.lineage, UsedInputReceipt("integrated_statistics", identity,
        "application/vnd.stratbox.dataset+json", "inline", version=identity))
    batch = ObservationBatch("cbr.statistics.derived", 1, computation.sha256, tuple(observations), lineage,
        tuple(use for source in dataset.batches for use in source.source_uses))
    return StatisticsDataset((batch,), dataset.inputs, dataset.mapping_version, dataset.diagnostics, method)


def calculate_change(dataset, before, after, *, method="absolute", release_ids=()):
    if (not isinstance(before, PeriodRef) or not isinstance(after, PeriodRef)
            or method not in {"absolute", "growth_percent"} or before.kind != after.kind
            or (before.as_of or before.end) >= (after.as_of or after.end)):
        raise ValueError("cbr.statistics.change_selection_invalid")
    groups = {}
    for item in _selected(dataset, release_ids):
        if item.period not in {before, after}:
            continue
        key = (item.subject, item.metric, _dimensions(item), item.perimeter)
        pair = groups.setdefault(key, {})
        if item.period in pair:
            raise ValueError("cbr.statistics.revision_selection_required")
        pair[item.period] = item
    result = []
    for key, pair in groups.items():
        if set(pair) != {before, after}:
            continue
        left, right = pair[before], pair[after]
        old, new = _numeric(left), _numeric(right)
        if method == "growth_percent" and old == 0:
            raise ValueError("cbr.statistics.zero_denominator")
        value = _compute(old, new, method)
        metric = MetricRef(right.metric.id + ".computed_" + method,
            right.metric.unit if method == "absolute" else "percent",
            None if method == "absolute" else "ratio", "cbr.statistics.change.v1",
            right.metric.scale if method == "absolute" else Decimal(1))
        dimensions = dict(right.dimensions)
        dimensions["measure_basis"] = "computed_" + method
        dimensions["baseline_period"] = str(before.as_of or before.start) + ("/" + str(before.end) if before.end else "")
        _retain_evidence(dimensions, left, "baseline_")
        evidence = right.evidence_ref + "|baseline:" + left.evidence_ref
        result.append(Observation(right.subject, metric, after, tuple(sorted(dimensions.items())),
                                  right.perimeter, value, "derived", evidence))
    if not result:
        raise ValueError("cbr.statistics.no_compatible_period_pairs")
    return _finish(dataset, result, "cbr.statistics.change.v1", {
        "method": method, "before": [before.kind, before.as_of, before.start, before.end],
        "after": [after.kind, after.as_of, after.start, after.end], "release_ids": release_ids,
        "arithmetic": "exact_difference_or_decimal28_half_even"})


def calculate_share(dataset, numerator_metric, denominator_metric, *, release_ids=()):
    if numerator_metric == denominator_metric:
        raise ValueError("cbr.statistics.share_selection_invalid")
    groups = {}
    for item in _selected(dataset, release_ids):
        if item.metric.id not in {numerator_metric, denominator_metric}:
            continue
        # Explicit metric selection supplies the relationship; all other semantic
        # axes must agree. Source hierarchy labels are metric-local evidence.
        dimensions = _dimensions(item, share=True)
        key = (item.subject, item.period, dimensions, item.perimeter)
        pair = groups.setdefault(key, {})
        if item.metric.id in pair:
            raise ValueError("cbr.statistics.revision_selection_required")
        pair[item.metric.id] = item
    result = []
    for _, pair in groups.items():
        if set(pair) != {numerator_metric, denominator_metric}:
            continue
        numerator, denominator = pair[numerator_metric], pair[denominator_metric]
        if (numerator.metric.unit, numerator.metric.scale, numerator.metric.quantity_kind) != (
                denominator.metric.unit, denominator.metric.scale, denominator.metric.quantity_kind):
            raise ValueError("cbr.statistics.share_measure_mismatch")
        if numerator.metric.quantity_kind in {None, "ratio", "index"}:
            raise ValueError("cbr.statistics.share_measure_not_additive")
        divisor = _numeric(denominator)
        if divisor == 0:
            raise ValueError("cbr.statistics.zero_denominator")
        metric = MetricRef(numerator.metric.id + ".computed_share", "percent", "ratio", "cbr.share.v1", Decimal(1))
        dimensions = dict(numerator.dimensions)
        dimensions.update(measure_basis="computed_share", denominator_metric=denominator_metric)
        _retain_evidence(dimensions, denominator, "denominator_")
        result.append(replace(numerator, metric=metric, dimensions=tuple(sorted(dimensions.items())),
                              value=_compute(_numeric(numerator), divisor, "share"), value_status="derived", raw_token=None,
                              evidence_ref=numerator.evidence_ref + "|denominator:" + denominator.evidence_ref))
    if not result:
        raise ValueError("cbr.statistics.no_compatible_share_pairs")
    return _finish(dataset, result, "cbr.statistics.share.v1", {
        "numerator": numerator_metric, "denominator": denominator_metric, "release_ids": release_ids,
        "arithmetic": "decimal28_half_even"})
