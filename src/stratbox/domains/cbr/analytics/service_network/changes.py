"""Count changes over comparable cells, without inferring individual office events."""
from dataclasses import dataclass
from decimal import Decimal
from stratbox.shared.data.observations import ObservationBatch, Observation, MetricRef
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.core.execution import OperationFailure

@dataclass(frozen=True, slots=True)
class OfficeChangesRequest:
    baseline: ObservationBatch
    candidate: ObservationBatch
    dataset_id: str
    version_id: str

@dataclass(frozen=True, slots=True)
class OfficeChanges:
    batch: ObservationBatch
    matched_cells: int
    baseline_only: int
    candidate_only: int


def calculate(request):
    dependencies = tuple(UsedInputReceipt(role, observation_snapshot(batch).identity,
        "application/vnd.stratbox.dataset+json", "inline", batch.dataset_id)
        for role, batch in (("baseline_observations", request.baseline), ("candidate_observations", request.candidate)))
    def indexed(batch):
        result = {}
        for observation in batch.observations:
            if observation.metric.quantity_kind != "count":
                raise OperationFailure("source.office_comparison_count_required")
            key = observation.subject, observation.metric, observation.dimensions, observation.perimeter
            if key in result:
                raise OperationFailure("source.office_comparison_requires_one_period")
            result[key] = observation
        return result
    before, after = indexed(request.baseline), indexed(request.candidate)
    common = before.keys() & after.keys()
    if not common:
        raise OperationFailure("source.office_comparison_scope_disjoint")
    observations = []
    for key in sorted(common, key=repr):
        old, new = before[key], after[key]
        if old.period.kind != new.period.kind:
            raise OperationFailure("source.office_comparison_period_incompatible")
        if (old.value_status == new.value_status == "reported"
                and type(old.value) in {int, Decimal} and type(new.value) in {int, Decimal}):
            value, status = new.value - old.value, "derived"
        else:
            value, status = None, "missing"
        dimensions = new.dimensions + (("baseline_period", str(old.period)),)
        observations.append(Observation(new.subject,
            MetricRef("change." + new.metric.id, new.metric.unit, "count", "cbr.office_count_change.v1", new.metric.scale),
            new.period, dimensions, new.perimeter, value, status,
            f"baseline:{old.evidence_ref};candidate:{new.evidence_ref}"))
    inputs = tuple(dict.fromkeys((*request.baseline.lineage, *request.candidate.lineage, *dependencies)))
    return OfficeChanges(ObservationBatch(request.dataset_id, 1, request.version_id, tuple(observations), inputs),
                         len(common), len(before.keys() - common), len(after.keys() - common))
