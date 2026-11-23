"""Exact same-period revision deltas; cross-period growth requires a separate model."""
from dataclasses import replace
from stratbox.shared.data.calculations import compare_observations
from stratbox.shared.data.observations import Observation, ObservationBatch
from stratbox.shared.evidence import UsedInputReceipt


def calculate(request):
    comparison = compare_observations(request.before, request.after)
    observations = []
    for change in comparison.changes:
        source = change.after if change.after is not None else change.before
        reserved = {"calculation", "change_kind", "qualification", "before_value", "after_value"}
        if reserved & dict(source.dimensions).keys():
            raise ValueError("frg.calculation.already_calculated")
        before = change.before.value if change.before is not None else None
        after = change.after.value if change.after is not None else None
        dimensions = (*source.dimensions, ("calculation", "frg.revision_delta.v1"), ("change_kind", change.kind),
            ("qualification", change.qualification or "same_full_semantic_key"),
            ("before_value", str(before) if before is not None else ""),
            ("after_value", str(after) if after is not None else ""))
        metric = replace(source.metric, id=source.metric.id + ".revision_delta", definition_version="frg.revision_delta.v1")
        evidence = f"sha256:{comparison.before_identity.sha256}..sha256:{comparison.after_identity.sha256}"
        observations.append(Observation(source.subject, metric, source.period, dimensions, source.perimeter,
            change.delta, "derived" if change.delta is not None else "not_applicable", evidence))
    lineage = tuple(dict.fromkeys((*request.before.lineage, *request.after.lineage,
        UsedInputReceipt("before_integrated", comparison.before_identity, "application/vnd.stratbox.dataset+json", "inline", request.before.dataset_id),
        UsedInputReceipt("after_integrated", comparison.after_identity, "application/vnd.stratbox.dataset+json", "inline", request.after.dataset_id))))
    return ObservationBatch(request.dataset_id, 1, request.release_id, tuple(observations), lineage)
