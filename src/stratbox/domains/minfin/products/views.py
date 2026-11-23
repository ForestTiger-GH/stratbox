"""Prepare already-calculated values without reopening source workbooks."""
from decimal import Decimal

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, SubjectRef
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.data.views import prepare_observation_view
from stratbox.shared.evidence import UsedInputReceipt
from ..analytics.snapshots import validate_summary, summary_snapshot
from ..integration.observations import economic_period
from ..tables.periods import preceding_year


def prepare_view(request):
    summary = request.summary
    validate_summary(summary)
    retained = summary_snapshot(summary, dataset_id=summary.source_id + ".headlines", version_id=summary.period_id)
    period = economic_period(summary.period_id, summary.frequency, summary.value_basis)
    prior = economic_period(preceding_year(summary.period_id), summary.frequency, summary.value_basis)
    metric_ids = request.metric_ids or tuple(x.metric_id for x in summary.metrics)
    if len(set(metric_ids)) != len(metric_ids) or any(x not in {m.metric_id for m in summary.metrics} for x in metric_ids):
        raise ValueError("minfin.view.selection_invalid")
    rows = []
    for item in summary.metrics:
        if item.metric_id not in metric_ids:
            continue
        metric = MetricRef(item.metric_id, "RUB", "stock" if summary.value_basis == "stock" else "flow",
                           str(summary.calculation_version), Decimal("1e9"))
        base_dims = (("source_series", summary.source_id), ("value_basis", summary.value_basis), ("comparison", item.comparison))
        evidence = f"sha256:{retained.identity.sha256}#metric={item.metric_id}"
        rows.append(Observation(SubjectRef("publisher_series", summary.source_id), metric, period,
                                (*base_dims, ("measure", "current")), summary.family_id,
                                Decimal(item.value), "derived", evidence))
        rows.append(Observation(SubjectRef("publisher_series", summary.source_id), metric, prior,
                                (*base_dims, ("measure", "previous_year")), summary.family_id,
                                Decimal(item.previous_year_value) if item.previous_year_value is not None else None,
                                "derived" if item.previous_year_value is not None else "missing", evidence))
        rows.append(Observation(SubjectRef("publisher_series", summary.source_id),
                                MetricRef(item.metric_id + ".yoy_pct", "percent", "ratio", str(summary.calculation_version), Decimal(1)),
                                period, (*base_dims, ("measure", "year_on_year")), summary.family_id,
                                Decimal(item.yoy_pct) if item.yoy_pct is not None else None,
                                "derived" if item.yoy_pct is not None else "not_applicable", evidence))
    batch = ObservationBatch(summary.source_id + ".headlines", 1, summary.period_id, tuple(rows),
        (UsedInputReceipt("calculation_result", retained.identity, "application/vnd.stratbox.dataset+json", "inline", summary.source_id),
         *retained.manifest.inputs))
    return prepare_observation_view(batch, view_id=request.view_id,
        coverage=SnapshotCoverage("complete", "All requested metrics, prior values and growth qualifications."),
        qualifications=("source_headlines", "prior_comparison_status_retained"))
