"""Prepare numerical histories and qualify typed seasonal adjustment results."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import AdjustmentDiagnostics, Assessment, TimeSeries, TimeSeriesAdjustment, fingerprint, select_dataset
from ._settings import _get, _option
from ._values import OBSERVATION_GRAIN, _grain_key, _rows


def timeseries_prepare(inputs, settings, context):
    dataset = inputs["observations"]
    selected = dict(_option(context, settings, "selection", {}))
    rows = [row for row in _rows(dataset) if all(row.get(k) == v for k, v in selected.items())]
    grain = _get(settings, "group_by", OBSERVATION_GRAIN)
    coordinates = {_grain_key(row,grain) for row in rows}
    if len(coordinates) != 1:
        raise ExecutionFailure("timeseries.unique_grain_required")
    rows.sort(key=lambda row: str(row["period"]))
    sample = rows[0]
    dataset = select_dataset(dataset,rows)
    series = TimeSeries({key:sample.get(key) for key in grain}, tuple(row["period"] for row in rows), tuple(row.get("value") for row in rows),
        sample.get("unit", ""), sample.get("frequency", ""), sample.get("measure_kind", ""), (*dataset.lineage, dataset.identity), dataset.assessment, source_uses=dataset.source_uses)
    return {"series": series, "assessment": series.assessment}


def timeseries_partition(inputs, settings, context):
    dataset = inputs.get("dataset", inputs.get("observations"))
    group = _get(settings, "group_by", OBSERVATION_GRAIN)
    groups = defaultdict(list)
    for row in _rows(dataset):
        groups[_grain_key(row,group)].append(row)
    results = []
    for key in sorted(groups, key=str):
        selected = select_dataset(dataset, groups[key])
        results.append(timeseries_prepare({"observations": selected}, settings, context)["series"])
    return {"items": tuple(results)}


def timeseries_validate(inputs, settings, context):
    series = inputs["series"]
    if not series.unit or not series.frequency or not series.measure_kind:
        raise ExecutionFailure("timeseries.semantics_required")
    if len(series.values) < _option(context, settings, "minimum_periods", 1):
        raise ExecutionFailure("timeseries.insufficient_history")
    if any(value is None for value in series.values) and _get(settings, "missingness", "reject") == "reject":
        raise ExecutionFailure("timeseries.missing_values")
    return {"assessment": Assessment()}


def timeseries_adjust(inputs, settings, context):
    timeseries_validate(inputs, settings, context)
    provider = context.provider("seasonal_adjustment")
    original = inputs["series"]
    result = provider.adjust(original, settings=settings, checkpoint=context.checkpoint)
    _validate_adjustment(result, settings)
    if result.input_identity != fingerprint(original): raise ExecutionFailure("timeseries.adjustment_input_mismatch")
    return {"adjustment": result}


def _validate_adjustment(adjustment, settings):
    if not isinstance(adjustment, TimeSeriesAdjustment) or not isinstance(adjustment.diagnostics, AdjustmentDiagnostics):
        raise ExecutionFailure("timeseries.typed_adjustment_required")
    original, adjusted = adjustment.original, adjustment.adjusted
    if not adjustment.method or adjustment.input_identity != fingerprint(original) or adjustment.diagnostics.input_identity != adjustment.input_identity:
        raise ExecutionFailure("timeseries.adjustment_input_mismatch")
    if (original.periods != adjusted.periods or original.frequency != adjusted.frequency or original.coordinates != adjusted.coordinates
            or original.unit != adjusted.unit or original.measure_kind != adjusted.measure_kind):
        raise ExecutionFailure("timeseries.adjustment_semantic_mismatch")
    if len(adjusted.values) != len(original.values) or any(value is None or not Decimal(value).is_finite() for value in adjusted.values):
        raise ExecutionFailure("timeseries.adjustment_invalid_values")
    required = set(_get(settings, "required_diagnostics", ("residual_seasonality", "outlier_policy")))
    if not required or not required <= adjustment.diagnostics.checks.keys() or not all(adjustment.diagnostics.checks[key] for key in required):
        raise ExecutionFailure("timeseries.diagnostics_not_admitted")
    if not adjustment.assessment.complete or not adjustment.diagnostics.assessment.complete:
        raise ExecutionFailure("timeseries.adjustment_not_admitted")


def timeseries_diagnose(inputs, settings, context):
    adjustment = inputs["adjustment"]
    _validate_adjustment(adjustment, settings)
    return {"diagnostics": adjustment.diagnostics}
