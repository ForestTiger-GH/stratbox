"""Map office observations explicitly; publisher names remain available."""
from dataclasses import asdict
from stratbox.core.execution import OperationFailure
from stratbox.shared.data.observations import Observation, ObservationBatch, MetricRef
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


def align(request, invocation):
    value = request.release
    if (value.batch is None or value.qualification is None
            or value.qualification.analysis == "literal_only"
            or value.dataset_version.dataset_id not in {"cbr.offices", "cbr.offices_reg"}):
        raise OperationFailure("source.office_observations_unqualified")
    subjects = {item.source: item for item in request.subjects}
    regions = {item.source_label: item for item in request.regions}
    metrics = {item.source_id: item for item in request.metrics}
    if (len(subjects) != len(request.subjects) or len(regions) != len(request.regions)
            or len(metrics) != len(request.metrics)
            or any(not item.edition for item in (*request.subjects, *request.regions, *request.metrics))):
        raise OperationFailure("request.office_mapping_invalid")
    observations, seen = [], set()
    invocation.stage("align")
    for receipt in value.inputs:
        invocation.use(receipt)
    invocation.use(UsedInputReceipt("source_office_observations", observation_snapshot(value.batch).identity,
        "application/vnd.stratbox.dataset+json", "inline", value.batch.dataset_id,
        version=value.dataset_version.identity))
    invocation.use(UsedInputReceipt.for_payload(SourcePayload(canonical_manifest_bytes({
        "subjects": [asdict(item) for item in request.subjects],
        "regions": [asdict(item) for item in request.regions],
        "metrics": [asdict(item) for item in request.metrics],
    }), "application/json"), "office_mapping_editions"))
    for item in value.batch.observations:
        invocation.check_cancelled()
        mapping = subjects.get(item.subject)
        subject = mapping.target if mapping else item.subject
        dimensions = list(item.dimensions)
        dimensions.extend((("source_subject_namespace", item.subject.namespace), ("source_subject_id", item.subject.id)))
        if mapping:
            dimensions.append(("subject_mapping_edition", mapping.edition))
        source_label = item.subject.id if item.subject.namespace == "cbr.published_territory" else dict(item.dimensions).get("region")
        geography = regions.get(source_label)
        if geography:
            dimensions.extend((("geography_id", geography.region_id), ("geography_edition", geography.edition)))
        elif source_label:
            if request.require_geography:
                raise OperationFailure("source.office_geography_unresolved")
            dimensions.append(("geography_status", "unresolved"))
        metric_mapping = metrics.get(item.metric.id)
        if metric_mapping:
            target = metric_mapping.target
            if (target.unit != item.metric.unit or target.scale != item.metric.scale
                    or target.quantity_kind not in {None, "count"}):
                raise OperationFailure("request.office_mapping_changes_measure")
            metric = MetricRef(target.id, target.unit, "count", target.definition_version or metric_mapping.edition, target.scale)
            dimensions.append(("metric_mapping_edition", metric_mapping.edition))
        else:
            metric = MetricRef(item.metric.id, item.metric.unit, "count", "cbr.office_source_counts.v1", item.metric.scale)
        if len({key for key, _ in dimensions}) != len(dimensions):
            raise OperationFailure("source.office_dimension_collision")
        observation = Observation(subject, metric, item.period, tuple(dimensions), item.perimeter,
            item.value, item.value_status, item.evidence_ref, item.raw_token)
        key = subject, metric, item.period, tuple(dimensions), item.perimeter
        if key in seen:
            raise OperationFailure("source.office_duplicate_observation")
        seen.add(key)
        observations.append(observation)
    batch = ObservationBatch(request.dataset_id, 1, request.version_id, tuple(observations), tuple(invocation.used_inputs))
    invocation.budget.charge("objects", len(observations))
    invocation.record(ByteIdentity.of(canonical_manifest_bytes(asdict(batch))))
    return batch
