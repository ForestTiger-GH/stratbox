"""Select, qualify, align and combine semantic observation values."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, TableEvidenceSet
from stratbox.shared.data.selection import select_observations
from stratbox.shared.data.history import (HistoryMembership, history_members, history_certificates,
    stable_semantics, resolve_revisions, verify_history_certificates)
from ._settings import _get, _option
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
    if getattr(dataset, "validation_certificates", ()):
        verify = getattr(context, "verify_validation_certificate", lambda certificate: False)
        if not verify_history_certificates(dataset, verify):
            raise ExecutionFailure("validation.history_evidence_unverified")
    expected = tuple(_option(context, settings, "expected_issues", ()))
    if expected:
        from dataclasses import replace
        members = history_members((dataset,))
        actual = tuple(dict.fromkeys(member.issue_id for member in members))
        missing = tuple(issue for issue in expected if issue not in actual)
        previous = getattr(dataset, "history_membership", None)
        membership = HistoryMembership(members, expected, missing,
            previous.revisions if isinstance(previous, HistoryMembership) else (),
            previous.policy_identity if isinstance(previous, HistoryMembership) else None)
        dataset = replace(dataset, history_membership=membership, assessment=replace(dataset.assessment,
            status="partial" if missing else dataset.assessment.status, expected=expected, observed=actual))
    return {"dataset": dataset, "assessment": dataset.assessment}


def observations_select(inputs, settings, context):
    query = inputs.get("query")
    if query is None:
        query = _option(context, settings, "query")
    if query is None:
        raise ExecutionFailure("selection.explicit_query_required")
    result = select_observations(inputs["dataset"], query)
    return {"dataset": result, "assessment": result.assessment, "coverage": result.assessment.coverage}


def observations_resolve_revisions(inputs, settings, context):
    policy = inputs.get("policy")
    if policy is None:
        policy = _option(context, settings, "policy")
    if policy is None:
        raise ExecutionFailure("history.explicit_policy_required")
    result, decisions = resolve_revisions(inputs["datasets"], policy)
    return {"dataset": result, "datasets": (result,), "decisions": decisions, "assessment": result.assessment}


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
    if any(stable_semantics(item) != stable_semantics(datasets[0]) for item in datasets):
        raise ExecutionFailure("observations.semantic_mismatch")
    members = history_members(datasets)
    issues = tuple(dict.fromkeys(member.issue_id for member in members))
    semantics = stable_semantics(datasets[0])
    assessments = tuple(item.assessment for item in datasets)
    assessment = Assessment("complete" if all(item.complete for item in assessments) else "partial",
        tuple(dict.fromkeys(f for item in assessments for f in item.findings)),
        qualifications=frozenset.intersection(*(item.qualifications for item in assessments))
        | frozenset({"partitioned_input_coverage"}))
    result = SourceDataset(datasets[0].source_id, tuple(row for item in datasets for row in item.rows),
        semantics, issue_id=issues[0] if len(issues) == 1 else "multi_issue_history", lineage=tuple(item.identity for item in datasets),
        assessment=assessment,
        source_uses=tuple(dict.fromkeys(use for item in datasets for use in item.source_uses)),
        validation_certificates=history_certificates(datasets), history_membership=HistoryMembership(members))
    observations_validate({"dataset": result}, settings, context)
    return {"dataset": result, "assessment": result.assessment}
