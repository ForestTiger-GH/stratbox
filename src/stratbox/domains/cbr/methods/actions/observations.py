"""Series-local qualification and explicit shared-address mapping."""
from dataclasses import replace
from datetime import date
from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, fingerprint


def validate(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.series_id:
        raise ValueError("cbr.dataset_source_mismatch")
    keys = set()
    for row in dataset.rows:
        context.checkpoint()
        key = (row.get("subject_namespace"), row.get("subject"), row.get("metric"),
            str(row.get("period")), row.get("perimeter"), row.get("dimensions", ()))
        if key in keys:
            raise ValueError("cbr.observation_duplicate")
        keys.add(key)
        if not row.get("evidence_ref") or not row.get("unit") or row.get("period") is None:
            raise ValueError("cbr.observation_semantics_incomplete")
        if (row.get("value_status") in {"reported", "derived", "reconstructed"}) != (row.get("value") is not None):
            raise ValueError("cbr.observation_status_mismatch")
    return {"dataset": dataset, "assessment": dataset.assessment}


def align(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.series_id:
        raise ValueError("cbr.dataset_source_mismatch")
    subjects = {(namespace, source): target for namespace, source, target in settings.subjects}
    metrics = dict(settings.metrics)
    rows, unresolved = [], set()
    for item in dataset.rows:
        context.checkpoint()
        row = dict(item)
        key = row.get("subject_namespace"), row.get("subject")
        period = row.get("period")
        start, end = period if isinstance(period, tuple) else (period, period)
        candidates = tuple(binding for binding in settings.bindings
            if (binding.source_namespace, binding.source_id) == key
            and (binding.valid_from is None or date.fromisoformat(str(start)) >= binding.valid_from)
            and (binding.valid_until is None or date.fromisoformat(str(end)) <= binding.valid_until))
        if len(candidates) > 1 or candidates and key in subjects:
            raise ValueError("cbr.subject_mapping_ambiguous")
        if candidates or key in subjects:
            row["source_subject"] = row["subject"]
            row["source_subject_namespace"] = row["subject_namespace"]
            row["subject"] = candidates[0].target_id if candidates else subjects[key]
            row["subject_namespace"] = candidates[0].target_namespace if candidates else "canonical"
            if candidates:
                row["subject_reference"] = candidates[0].reference_identity
        else:
            unresolved.add(str(key))
        if row.get("metric") in metrics:
            row["source_metric"] = row["metric"]
            row["metric"] = metrics[row["metric"]]
        rows.append(row)
    if settings.require_all and unresolved:
        raise ValueError("cbr.mapping_incomplete")
    assessment = Assessment("partial" if unresolved else "complete",
        ("cbr.source_local_identities_retained",) if unresolved else (), observed=tuple(sorted(unresolved)))
    result = IntegratedDataset(dataset.source_id, tuple(rows), dataset.semantics, dataset.issue_id,
        (*dataset.lineage, fingerprint(settings)), assessment, dataset.native, source_uses=dataset.source_uses)
    return {"dataset": result, "assessment": assessment}
