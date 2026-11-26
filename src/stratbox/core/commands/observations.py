"""Select, qualify, align and combine semantic observation values."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, TableEvidenceSet
from ._settings import _get
from ._values import OBSERVATION_GRAIN, _grain_key, _rows


def table_extract(inputs, settings, context):
    physical = inputs["physical"]
    if isinstance(physical, TableEvidenceSet):
        return {"tables": physical, "coverage": physical.assessment}
    raise ExecutionFailure("table.source_specification_required")


def table_interpret(inputs, settings, context):
    raise ExecutionFailure("table.semantic_specification_required")


def observations_validate(inputs, settings, context):
    dataset = inputs["dataset"]
    keys, grain = set(), _get(settings, "grain", ('period', *OBSERVATION_GRAIN))
    for row in _rows(dataset):
        key = _grain_key(row,grain)
        if key in keys:
            raise ExecutionFailure("observations.duplicate_grain")
        keys.add(key)
    return {"dataset": dataset, "assessment": dataset.assessment}


def observations_align(inputs, settings, context):
    dataset, rows = inputs["dataset"], []
    mappings = _get(settings, "mappings", {})
    for row in _rows(dataset):
        converted = dict(row)
        for axis, mapping in mappings.items():
            if converted.get(axis) not in mapping:
                raise ExecutionFailure("mapping.unresolved:" + axis)
            converted[axis] = mapping[converted[axis]]
        rows.append(converted)
    result = IntegratedDataset(dataset.source_id, tuple(rows), dataset.semantics, dataset.issue_id,
                               (*dataset.lineage, dataset.identity), dataset.assessment, source_uses=dataset.source_uses)
    observations_validate({"dataset": result}, settings, context)
    return {"dataset": result, "assessment": result.assessment}


def observations_merge(inputs, settings, context):
    datasets = inputs["datasets"]
    if not datasets or any(not isinstance(item, SourceDataset) for item in datasets):
        raise ExecutionFailure("observations.datasets_required")
    if len(datasets) == 1:
        return {"dataset": datasets[0], "assessment": datasets[0].assessment}
    source_ids = {item.source_id for item in datasets}
    if len(source_ids) != 1 and not _get(settings, "allow_cross_source", False):
        raise ExecutionFailure("observations.source_mismatch")
    if any(item.semantics != datasets[0].semantics for item in datasets):
        raise ExecutionFailure("observations.semantic_mismatch")
    issues = tuple(dict.fromkeys(item.issue_id for item in datasets))
    semantics = dict(datasets[0].semantics)
    if len(issues) > 1: semantics["source_issues"] = issues
    assessments = tuple(item.assessment for item in datasets)
    assessment = Assessment("complete" if all(item.complete for item in assessments) else "partial",
        tuple(dict.fromkeys(f for item in assessments for f in item.findings)),
        qualifications=frozenset.intersection(*(item.qualifications for item in assessments))
        | frozenset({"partitioned_input_coverage"}))
    result = SourceDataset(datasets[0].source_id, tuple(row for item in datasets for row in item.rows),
        semantics, issue_id=issues[0] if len(issues) == 1 else "multi_issue_history", lineage=tuple(item.identity for item in datasets),
        assessment=assessment,
        source_uses=tuple(dict.fromkeys(use for item in datasets for use in item.source_uses)))
    observations_validate({"dataset": result}, settings, context)
    return {"dataset": result, "assessment": result.assessment}
