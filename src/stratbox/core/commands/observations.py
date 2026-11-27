"""Select, qualify, align and combine semantic observation values."""
from __future__ import annotations
from collections.abc import Mapping
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, TableEvidenceSet
from stratbox.shared.data.selection import select_observations
from stratbox.shared.data.history import (HistoryLimits, history_grain, merge_histories, resolve_revisions,
    set_history_expectations, validate_history_view, verify_history_certificates)
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
    validate_history_view(dataset)
    keys, grain = set(), _option(context, settings, "grain", history_grain(dataset) or ('period', *OBSERVATION_GRAIN))
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
    expected_members = tuple(_option(context, settings, "expected_members", ()))
    if expected or expected_members:
        dataset = set_history_expectations(dataset, expected, expected_members)
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
    limits = _option(context, settings, "history_limits", HistoryLimits())
    if isinstance(limits, Mapping):
        limits = HistoryLimits(**limits)
    result = merge_histories(datasets, allow_cross_source=_option(context, settings, "allow_cross_source", False),
        grain=_option(context, settings, "grain", ()), limits=limits)
    observations_validate({"dataset": result}, settings, context)
    return {"dataset": result, "assessment": result.assessment}
