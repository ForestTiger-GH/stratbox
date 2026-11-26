"""Exact arithmetic over admitted observations with explicit scientific semantics."""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
import ast
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, SourceDataset
from ._settings import _get, _option
from ._values import OBSERVATION_GRAIN, _derivation_assessment, _derived, _grain_key, _rows


def observations_compare(inputs, settings, context):
    before, after = inputs["before"], inputs["after"]
    grain = _get(settings, "grain", ('period', *OBSERVATION_GRAIN))
    sides = []
    for dataset in (before, after):
        values = {}
        for row in _rows(dataset):
            key = _grain_key(row,grain)
            if key in values:
                raise ExecutionFailure("comparison.duplicate_grain")
            values[key] = row
        sides.append(values)
    left, right = sides
    changes = []
    def semantic(row):
        return None if row is None else (row.get("value"), row.get("value_status"), row.get("raw_token"))
    for key in dict.fromkeys((*left, *right)):
        a, b = left.get(key), right.get(key)
        if semantic(a) == semantic(b): continue
        delta = None
        if a is not None and b is not None and a.get("value") is not None and b.get("value") is not None:
            delta = _number(b) - _number(a)
        changes.append({"key": key, "before": a, "after": b, "delta": delta,
                        "kind": "added" if a is None else "removed" if b is None else "changed"})
    return {"changes": tuple(changes), "assessment": _derivation_assessment(before, after)}


def _number(row):
    value = row.get("value")
    if value is None or type(value) is bool or row.get("value_status") in {"missing", "dash", "suppressed", "withheld"}:
        raise ExecutionFailure("calculation.numeric_value_required")
    number = Decimal(value)
    if not number.is_finite():
        raise ExecutionFailure("calculation.nonfinite")
    return number


def calculate_change(inputs, settings, context):
    dataset = inputs["observations"]
    required_kind = _get(settings, "required_measure_kind")
    if required_kind and any(row.get("measure_kind") != required_kind for row in dataset.rows):
        raise ExecutionFailure("calculation.measure_kind_mismatch")
    grain = _get(settings, "group_by", OBSERVATION_GRAIN)
    groups, result = defaultdict(list), []
    for row in _rows(dataset):
        groups[_grain_key(row,grain)].append(row)
    before, after, mode = _option(context, settings, "before"), _option(context, settings, "after"), _get(settings, "mode", "absolute")
    if (before is None) != (after is None) or before is not None and str(before) >= str(after):
        raise ExecutionFailure("calculation.change_selection_invalid")
    for rows in groups.values():
        rows.sort(key=lambda row: str(row["period"]))
        periods = [row["period"] for row in rows]
        if len(periods) != len(set(periods)):
            raise ExecutionFailure("calculation.duplicate_period")
        if before is not None:
            by_period = {row['period']: row for row in rows}
            if before not in by_period or after not in by_period:
                raise ExecutionFailure('calculation.selected_period_missing')
            pairs = [(by_period[before], by_period[after])]
        else:
            pairs = list(zip(rows, rows[1:]))
        for first, last in pairs:
            if _get(settings, "same_window", _get(settings, "same_accumulation_window", False)):
                def window(row):
                    period = row["period"]
                    if isinstance(period, tuple): return tuple(str(part)[4:] for part in period)
                    return str(period)[4:]
                if window(first) != window(last):
                    raise ExecutionFailure("calculation.accumulation_window_mismatch")
            a, b = _number(first), _number(last)
            if mode not in {"absolute", "percent"}: raise ExecutionFailure("calculation.invalid_change_mode")
            status = "prior_zero" if a == 0 else "sign_change" if a < 0 < b or b < 0 < a else "comparable"
            value = b - a if mode == "absolute" else None if status != "comparable" else (b / a - 1) * 100
            row = {**dict(last), "value": value, "value_status": "derived" if value is not None else "undefined",
                           "comparison_period": first["period"], "calculation": mode, "comparison_status": status,
                           "baseline_evidence_ref": first.get("evidence_ref"), "baseline_value": first.get("value"),
                           "baseline_annotations": first.get("annotations", ()),
                           "metric": _get(settings, "output_metric", str(last.get("metric")) + (".change" if mode == "absolute" else ".growth"))}
            if mode == "percent":
                row.update(measure_kind="rate", unit="percent", scale=1)
            elif last.get("measure_kind") == "stock":
                row.update(measure_kind="net_change", period_kind="interval", period=(first["period"], last["period"]),
                    period_start=first["period"], period_end=last["period"], source_measure_kind="stock")
            else:
                row["measure_kind"] = "difference"
            result.append(row)
    if not result: raise ExecutionFailure("calculation.no_comparable_pair")
    return {"dataset": _derived(dataset, result)}


def calculate_index(inputs, settings, context):
    dataset, rows = inputs["observations"], []
    for row in _rows(dataset):
        if row.get("measure_kind") != "index":
            raise ExecutionFailure("calculation.index_required")
        rows.append({**dict(row), "metric": _get(settings, "output_metric", str(row.get("metric")) + ".growth"),
                     "value": _number(row) - Decimal(_get(settings, "base", 100)), "value_status": "derived", "measure_kind": "rate"})
    return {"dataset": _derived(dataset, rows)}


def calculate_flow(inputs, settings, context):
    dataset = inputs["observations"]
    if any(row.get("measure_kind") != "flow" or row.get("basis", row.get("value_basis")) not in {"ytd", "cumulative"} for row in dataset.rows):
        raise ExecutionFailure("calculation.cumulative_flow_required")
    groups, result = defaultdict(list), []
    grain = _get(settings, 'group_by', OBSERVATION_GRAIN)
    for row in dataset.rows:
        groups[_grain_key(row, grain)].append(row)
    def end(row):
        period = row.get("period_end", row["period"])
        period = period[-1] if isinstance(period, tuple) else period
        raw = str(period)
        if "Q" in raw:
            return int(raw[:4]), int(raw[-1]) * 3
        if len(raw) < 7: raise ExecutionFailure("calculation.explicit_flow_period_required")
        return int(raw[:4]), int(raw[5:7])
    for rows in groups.values():
        rows.sort(key=lambda row: str(row["period"]))
        previous = None
        for row in rows:
            year, month = end(row)
            frequency = row.get("frequency", _get(settings, "frequency", "monthly"))
            step = 3 if frequency == "quarterly" else 1 if frequency == "monthly" else None
            if step is None: raise ExecutionFailure("calculation.flow_frequency_unsupported")
            if not 1 <= month <= 12 or month % step:
                raise ExecutionFailure('calculation.flow_period_invalid')
            first = month == step
            if previous is None or end(previous)[0] != year:
                if not first:
                    raise ExecutionFailure("calculation.preceding_ytd_required")
                value = _number(row)
            else:
                if end(previous)[1] + step != month:
                    raise ExecutionFailure("calculation.ytd_period_gap")
                value = _number(row) - _number(previous)
            from datetime import timedelta
            import calendar
            end_day = date(year, month, calendar.monthrange(year, month)[1])
            start_day = date(year, month - step + 1, 1)
            result.append({**dict(row), "value": value, "value_status": "derived", "basis": "period_flow",
                "value_basis": "period_flow", "period_kind": "interval", "period": (start_day.isoformat(), end_day.isoformat()),
                "period_start": start_day.isoformat(), "period_end": end_day.isoformat(),
                "cumulative_evidence_ref": row.get("evidence_ref"),
                "preceding_cumulative_evidence_ref": previous.get("evidence_ref") if previous is not None and end(previous)[0] == year else None})
            previous = row
    return {"dataset": _derived(dataset, result)}


def calculate_ratio(inputs, settings, context):
    numerator, denominator = inputs["numerator"], inputs["denominator"]
    group = _get(settings, "group_by", ('period', *(name for name in OBSERVATION_GRAIN
        if name not in {'metric', 'unit', 'scale'})))
    required_kind = _get(settings, "required_measure_kind")
    if required_kind and any(row.get("measure_kind") != required_kind for item in (numerator, denominator) for row in item.rows):
        raise ExecutionFailure("ratio.measure_kind_mismatch")
    right = {}
    for row in _rows(denominator):
        key = _grain_key(row,group)
        if key in right:
            raise ExecutionFailure("ratio.ambiguous_denominator")
        right[key] = row
    result = []
    for row in _rows(numerator):
        matching = right.get(_grain_key(row,group))
        if matching is None or row.get("unit") != matching.get("unit") or row.get("scale", 1) != matching.get("scale", 1):
            raise ExecutionFailure("ratio.incompatible_inputs")
        if any(row.get(key) != matching.get(key) for key in OBSERVATION_GRAIN
               if key not in {'metric', 'unit', 'scale'}):
            raise ExecutionFailure("ratio.semantic_mismatch")
        den = _number(matching)
        value = _number(row) / den * Decimal(_get(settings, "multiplier", 1)) if den else None
        result.append({**dict(row), "metric": _get(settings, "output_metric", "ratio"), "unit": "ratio", "scale": 1,
            "value": value, "value_status": "derived" if value is not None else "undefined", "measure_kind": "ratio",
            "denominator_evidence_ref": matching.get("evidence_ref"), "denominator_metric": matching.get("metric"),
            "denominator_annotations": matching.get("annotations", ()), "denominator_value": matching.get("value")})
    from dataclasses import replace
    result = _derived(numerator,result,sources=(denominator.identity,))
    return {"dataset":replace(result,
        assessment=_derivation_assessment(numerator, denominator),
        source_uses=tuple(dict.fromkeys((*numerator.source_uses,*denominator.source_uses))))}


def calculate_formula(inputs, settings, context):
    dataset = inputs["dataset"]
    operands, group = _get(settings, "operands", {}), _get(settings, "group_by", ("period", "subject", "perimeter"))
    expression = ast.parse(_get(settings, "expression", ""), mode="eval")
    def evaluate(node, numbers):
        if isinstance(node, ast.Expression): return evaluate(node.body, numbers)
        if isinstance(node, ast.Name) and node.id in numbers: return numbers[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}: return Decimal(str(node.value)), {}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value, unit = evaluate(node.operand, numbers)
            return (-value if isinstance(node.op, ast.USub) else value), unit
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            (a, au), (b, bu) = evaluate(node.left, numbers), evaluate(node.right, numbers)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if au != bu: raise ExecutionFailure("formula.dimension_mismatch")
                return (a + b if isinstance(node.op, ast.Add) else a - b), au
            unit = dict(au)
            sign = -1 if isinstance(node.op, ast.Div) else 1
            for key, exponent in bu.items(): unit[key] = unit.get(key, 0) + sign * exponent
            unit = {key: exponent for key, exponent in unit.items() if exponent}
            if isinstance(node.op, ast.Mult): return a * b, unit
            if b == 0: raise ExecutionFailure("formula.zero_denominator")
            return a / b, unit
        raise ExecutionFailure("formula.expression_not_admitted")
    groups, result = defaultdict(dict), []
    for row in _rows(dataset):
        names = [name for name, metric in operands.items() if row.get("metric") == metric]
        for name in names:
            bucket = groups[_grain_key(row,group)]
            if name in bucket: raise ExecutionFailure("formula.duplicate_operand")
            bucket[name] = row
    for rows in groups.values():
        if set(rows) != set(operands): raise ExecutionFailure("formula.operand_missing")
        semantic = tuple(name for name in OBSERVATION_GRAIN if name not in {'metric', 'unit', 'scale'})
        if len({_grain_key(row, semantic) for row in rows.values()}) != 1:
            raise ExecutionFailure('formula.semantic_mismatch')
        units = {(row.get("unit"), row.get("scale", 1)) for row in rows.values()}
        if len(units) != 1 or next(iter(units))[0] != _get(settings, "unit"):
            raise ExecutionFailure("formula.incompatible_unit")
        value, dimensions = evaluate(expression, {name: (_number(row), {row["unit"]: 1}) for name, row in rows.items()})
        expected = {} if _get(settings, "unit") in {"ratio", "percent", "1"} else {_get(settings, "unit"): 1}
        if dimensions != expected: raise ExecutionFailure("formula.output_dimension_mismatch")
        result.append({**dict(next(iter(rows.values()))), "metric": _get(settings, "output_metric"),
                       "value": value, "value_status": "derived", "formula_inputs": tuple(operands.values())})
    if not result: raise ExecutionFailure("formula.no_eligible_group")
    return {"dataset": _derived(dataset, result)}


def _exact_calculation(method):
    """Deterministic precision independent of the caller's Decimal context."""
    from functools import wraps
    @wraps(method)
    def execute(inputs, settings, context):
        numbers = [row.get("value") for dataset in inputs.values() if isinstance(dataset, SourceDataset) for row in dataset.rows if row.get("value") is not None]
        precision = 80
        for value in numbers:
            try:
                item = Decimal(value)
                precision = max(precision, 3 * (len(item.as_tuple().digits) + abs(item.as_tuple().exponent)) + 40)
            except (TypeError, ValueError):
                pass
        if precision > 100000: raise ExecutionFailure("calculation.precision_limit")
        with localcontext() as decimal_context:
            decimal_context.prec = precision
            return method(inputs, settings, context)
    return execute


calculate_change = _exact_calculation(calculate_change)
calculate_ratio = _exact_calculation(calculate_ratio)
calculate_formula = _exact_calculation(calculate_formula)
calculate_flow = _exact_calculation(calculate_flow)
calculate_index = _exact_calculation(calculate_index)
observations_compare = _exact_calculation(observations_compare)
