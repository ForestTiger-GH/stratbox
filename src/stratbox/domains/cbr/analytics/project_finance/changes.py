"""Differences between explicit stock dates retain all release evidence."""
from dataclasses import replace
from decimal import Decimal

from stratbox.shared.data.observations import MetricRef, ObservationBatch, PeriodRef
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.domains.cbr.analytics.statistics.changes import _compute


def calculate(batch, before, after, metric_ids, *, method='absolute'):
    if (not isinstance(batch, ObservationBatch) or not isinstance(before, PeriodRef)
            or not isinstance(after, PeriodRef) or before.kind != 'as_of' or after.kind != 'as_of'
            or before.as_of >= after.as_of or method not in {'absolute', 'growth_percent'}
            or not isinstance(metric_ids, tuple) or not metric_ids or len(set(metric_ids)) != len(metric_ids)):
        raise ValueError('escrow.change_selection_invalid')
    selected = set(metric_ids)
    if selected - {item.metric.id for item in batch.observations}:
        raise ValueError('escrow.change_metric_unknown')
    groups = {}
    for item in batch.observations:
        if item.metric.id not in selected or item.period not in {before, after}:
            continue
        if (item.metric.quantity_kind not in {'stock', 'count', 'ratio', 'index'}
                or item.metric.scale is None or item.value_status not in {'reported', 'derived'}
                or type(item.value) not in {int, Decimal}
                or dict(item.dimensions).get('source_period_basis') != 'reporting_date'):
            raise ValueError('escrow.change_input_unqualified')
        dimensions = tuple(pair for pair in item.dimensions if pair[0] != 'source_status')
        key = (item.subject, item.metric, dimensions, item.perimeter)
        group = groups.setdefault(key, {})
        if item.period in group:
            raise ValueError('escrow.change_revision_selection_required')
        group[item.period] = item
    observations = []
    for (_, metric, dimensions, _), group in groups.items():
        if set(group) != {before, after}:
            raise ValueError('escrow.change_period_missing')
        left, right = group[before], group[after]
        if method == 'growth_percent' and left.value == 0:
            raise ValueError('escrow.change_zero_baseline')
        evidence = ByteIdentity.of(canonical_manifest_bytes({'method': method,
            'before': left.evidence_ref, 'after': right.evidence_ref,
            'before_value': left.value, 'after_value': right.value}))
        derived_metric = MetricRef(metric.id + '.' + method,
            metric.unit if method == 'absolute' else 'percent', None if method == 'absolute' else 'ratio',
            'cbr.escrow.change.v1', metric.scale if method == 'absolute' else Decimal(1))
        observations.append(replace(right, metric=derived_metric,
            period=PeriodRef('interval', start=before.as_of, end=after.as_of),
            dimensions=(*dimensions, ('computed_basis', 'difference_between_stock_dates'),
                        ('before_date', before.as_of.isoformat()), ('after_date', after.as_of.isoformat())),
            value=_compute(Decimal(left.value), Decimal(right.value), method), value_status='derived',
            evidence_ref=evidence.sha256, raw_token=None))
    if not observations:
        raise ValueError('escrow.change_no_observations')
    identity = ByteIdentity.of(canonical_manifest_bytes({'input_release': batch.release_id,
        'input_sources': [use.coordinate.material_identity.sha256 for use in batch.source_uses
            if use.coordinate.material_identity], 'method': method, 'before': before.as_of,
        'after': after.as_of, 'metric_ids': metric_ids}))
    return ObservationBatch(batch.dataset_id + '.change', 1, identity.sha256,
        tuple(observations), batch.lineage, batch.source_uses)
