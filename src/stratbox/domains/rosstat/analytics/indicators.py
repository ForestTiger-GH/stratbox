"""Explicit derivations and release comparison, separate from publisher indices."""
from dataclasses import dataclass, replace
from decimal import Decimal
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch
from ..integration.datasets import RosstatDataset, observation_key

@dataclass(frozen=True, slots=True)
class DatasetChange:
    key: tuple
    before: Observation | None
    after: Observation | None

@dataclass(frozen=True, slots=True)
class DatasetComparison:
    state: str
    changes: tuple[DatasetChange,...]
    reason: str


def compare_datasets(before: RosstatDataset, after: RosstatDataset) -> DatasetComparison:
    old={observation_key(v):v for v in before.batch.observations}
    new={observation_key(v):v for v in after.batch.observations}
    if len(old) != len(before.batch.observations) or len(new) != len(after.batch.observations):
        raise ValueError("rosstat.comparison_duplicate_observation")
    if {s.series_id for s in before.sources} != {s.series_id for s in after.sources}:
        raise ValueError("rosstat.comparison_family_mismatch")
    changes=[]
    for key in sorted(old.keys() | new.keys(),key=repr):
        a,b=old.get(key),new.get(key)
        # Evidence locators change between editions; compare statistical values,
        # units, source status and attached notes independently of the new hash.
        equivalent=a is not None and b is not None and (a.value,a.value_status,a.metric,a.dimensions,a.raw_token)==(b.value,b.value_status,b.metric,b.dimensions,b.raw_token)
        if not equivalent:
            changes.append(DatasetChange(key,a,b))
    state="changed" if changes else "unchanged"
    if before.coverage != after.coverage:
        state="indeterminate"
    return DatasetComparison(state,tuple(changes),"rosstat.dataset_scoped_comparison")


def derive_index_growth(dataset: RosstatDataset, *, release_id: str) -> ObservationBatch:
    values=[]
    for row in dataset.batch.observations:
        dimensions=dict(row.dimensions)
        if dimensions.get("measure") not in {"year_on_year_index","previous_period_index"}:
            continue
        if row.metric.quantity_kind != "index" or row.metric.unit != "percent" or row.metric.scale != Decimal(1):
            raise ValueError("rosstat.growth_index_basis_invalid")
        dimensions["derivation"]="published_percent_index_minus_100"
        dimensions["measure"]=dimensions["measure"].replace("_index","_growth")
        metric=MetricRef(row.metric.id + ".growth","percent","ratio","rosstat.index_growth.v1",Decimal(1))
        values.append(replace(row,metric=metric,value=row.value-Decimal(100) if row.value is not None else None,
            value_status="derived" if row.value is not None else row.value_status,
            dimensions=tuple(sorted(dimensions.items()))))
    if not values:
        raise ValueError("rosstat.growth_indices_required")
    return ObservationBatch(dataset.batch.dataset_id + ".growth",1,release_id,tuple(values),dataset.batch.lineage)
