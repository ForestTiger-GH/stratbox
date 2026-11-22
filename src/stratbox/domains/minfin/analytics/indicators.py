"""Headline extraction with period-safe prior-year comparisons."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, localcontext
from ..tables.periods import preceding_year
from ..tables.contracts import FlakeTable
from .contracts import HeadlineMetric, HeadlineSummary, SummaryRequest

def _number(value: str | None) -> Decimal | None:
    if value is None or not value.strip():
        return None
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("minfin.summary.invalid_numeric_value") from None
    if not number.is_finite():
        raise ValueError("minfin.summary.invalid_numeric_value")
    return number


def _row(flake: FlakeTable, code: str, starts_with: str):
    matching = [r for r in flake.rows if r.code.rstrip(".") == code]
    if len(matching) != 1:
        raise ValueError("minfin.summary.ambiguous_metric")
    item = matching[0]
    if not item.indicator.casefold().startswith(starts_with.casefold()):
        raise ValueError("minfin.summary.unexpected_metric_label")
    if len(item.values) != len(flake.columns):
        raise ValueError("minfin.summary.invalid_dimensions")
    return item


def _metric(metric_id: str, label: str, current: Decimal, prior: Decimal | None) -> HeadlineMetric:
    outcome = "comparable"
    delta = None
    if prior is None:
        outcome = "prior_missing"
    elif prior == 0:
        outcome = "prior_zero"
    elif current * prior < 0:
        outcome = "sign_change"
    else:
        with localcontext() as ctx:
            ctx.prec = 38
            delta = (current / prior - Decimal(1)) * 100
    # No implicit rounding of measurements or growth; the consumer chooses presentation precision.
    return HeadlineMetric(metric_id, label, format(current, "f"),
                          format(prior, "f") if prior is not None else None,
                          format(delta, "f") if delta is not None else None, outcome)


def summarize(request: SummaryRequest) -> HeadlineSummary:
    flake = request.flake
    periods = [col.period_id for col in flake.columns]
    if len(set(periods)) != len(periods) or not periods:
        raise ValueError("minfin.summary.invalid_periods")
    target = request.period_id or periods[-1]
    if target not in periods:
        raise ValueError("minfin.summary.period_unavailable")
    index = periods.index(target)
    prior_id = preceding_year(target)
    prior_index = periods.index(prior_id) if prior_id in periods else None
    if flake.family_id == "minfin.nwf":
        if flake.source_id != "minfin.nwf.flows" or flake.value_basis != "stock" or flake.frequency != "monthly":
            raise ValueError("minfin.summary.incompatible_basis")
        total = _row(flake, "2", "Объем на конец периода")
        other = _row(flake, "5", "Размещено в иные разрешенные активы на конец периода")
        now_total = _number(total.values[index]); now_other = _number(other.values[index])
        prev_total = _number(total.values[prior_index]) if prior_index is not None else None
        prev_other = _number(other.values[prior_index]) if prior_index is not None else None
        if now_total is None or now_other is None:
            raise ValueError("minfin.summary.missing_headline_value")
        if now_total < 0 or now_other < 0 or now_other > now_total:
            raise ValueError("minfin.summary.invalid_nwf_balance")
        if prev_total is not None and prev_other is not None and (prev_total < 0 or prev_other < 0 or prev_other > prev_total):
            raise ValueError("minfin.summary.invalid_nwf_balance")
        metrics = (
            _metric("nwf.total", "Объем ФНБ на конец периода", now_total, prev_total),
            _metric("nwf.liquid", "Ликвидные активы ФНБ", now_total - now_other,
                    prev_total - prev_other if prev_total is not None and prev_other is not None else None),
        )
    else:
        if flake.family_id not in {"minfin.fedbud", "minfin.conbud", "minfin.subbud"} or (
            (flake.frequency == "annual") != (flake.value_basis == "annual")
        ) or flake.value_basis not in {"ytd", "annual"}:
            raise ValueError("minfin.summary.incompatible_basis")
        labels = (
            ("1", "budget.revenue", "Доходы, всего"),
            ("2", "budget.expenditure", "Расходы, всего"),
            ("3", "budget.balance", "Дефицит (-)/Профицит (+)"),
        )
        current = []
        previous = []
        for code, title, label in labels:
            row = _row(flake, code, label)
            current.append(_number(row.values[index]))
            previous.append(_number(row.values[prior_index]) if prior_index is not None else None)
        if any(item is None for item in current):
            raise ValueError("minfin.summary.missing_headline_value")
        # Deficit (-) / surplus (+) must agree with income minus expense in the workbook.
        if abs(current[0] - current[1] - current[2]) > Decimal("0.05"):
            raise ValueError("minfin.summary.inconsistent_budget_totals")
        if all(value is not None for value in previous) and abs(previous[0] - previous[1] - previous[2]) > Decimal("0.05"):
            raise ValueError("minfin.summary.inconsistent_budget_totals")
        metrics = tuple(_metric(mid, label, now, prev) for (code, mid, label), now, prev in zip(labels, current, previous))
    return HeadlineSummary(flake.family_id, flake.source_id, target, flake.frequency,
                           flake.value_basis, flake.original_identity, flake.method_version, metrics)
