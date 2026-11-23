"""Prepared products consume integrated observations, with explicit date anchors."""
from dataclasses import replace
from stratbox.shared.data.views import ObservationView, prepare_observation_view
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from ..integration.datasets import RosstatDataset
from ..tables.profiles import KEP2_INDICATORS


def prepare_view(dataset: RosstatDataset, *, view_id="rosstat.observations", metric_ids=()) -> ObservationView:
    result=prepare_observation_view(dataset.batch,view_id=view_id,metric_ids=metric_ids,coverage=dataset.coverage)
    return replace(result,source_identity=dataset.identity)


def prepare_kep2_monthly(dataset: RosstatDataset) -> ObservationView:
    if any(source.series_id != "rosstat.short_term_indicators" for source in dataset.sources):
        raise ValueError("rosstat.kep2.view_series_mismatch")
    allowed={indicator.id for indicator in KEP2_INDICATORS}
    selected=[]
    for row in dataset.batch.observations:
        dims=dict(row.dimensions)
        if dims.get("frequency") != "monthly":
            continue
        if dims.get("indicator_id") not in allowed or dims.get("measure") not in {"absolute","year_on_year_index","previous_period_index"}:
            raise ValueError("rosstat.kep2.view_indicator_unreviewed")
        if row.subject.namespace != "iso3166-1" or row.subject.id != "RU":
            raise ValueError("rosstat.kep2.view_geography_mismatch")
        selected.append(row)
    if not selected:
        raise ValueError("rosstat.kep2.view_months_required")
    identity=dataset.identity
    receipt=UsedInputReceipt("integrated_dataset",identity,"application/vnd.stratbox.dataset","inline")
    batch=replace(dataset.batch,observations=tuple(selected),lineage=(*dataset.batch.lineage,receipt))
    return ObservationView("rosstat.kep2.monthly",batch,identity,
        SnapshotCoverage(dataset.coverage.status,"Monthly cells from the reviewed eleven-indicator KEP2 selection; annual and quarterly cells remain in the source flake and dataset."),
        ("display_date.next_period_start","published_indices.preserved","source_absence.preserved","frequency.monthly"))
