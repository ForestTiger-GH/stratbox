"""Source-local calculations dispatched by an explicit economic profile.

Same-period previous-year growth is shared; publisher-specific rows and
consistency checks stay in registered domain calculation methods.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, localcontext
from typing import TYPE_CHECKING

from ..tables.periods import preceding_year
from stratbox.shared.data.calculations import exact_difference
from ..tables.contracts import FlakeTable, SerializeFlakeRequest
from ..tables.flake_codec import serialize_flake
from .contracts import HeadlineMetric, HeadlineSummary, SummaryRequest
if TYPE_CHECKING:
    from .profiles import HeadlineProfile


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
    if (item.unit is not None and (item.unit != "RUB" or Decimal(item.scale) != Decimal("1e9"))
            or item.value_basis is not None and item.value_basis != flake.value_basis
            or flake.unit_hint == "mixed" and (item.unit is None or item.value_basis != "stock")):
        raise ValueError("minfin.summary.unit_or_basis_mismatch")
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
    elif (current < 0 < prior) or (prior < 0 < current):
        outcome = "sign_change"
    else:
        with localcontext() as ctx:
            ctx.prec = 38
            delta = (current / prior - Decimal(1)) * 100
    return HeadlineMetric(metric_id, label, format(current, "f"),
                          format(prior, "f") if prior is not None else None,
                          format(delta, "f") if delta is not None else None, outcome)


def budget_metrics(flake: FlakeTable, index: int, prior_index: int | None) -> tuple[HeadlineMetric, ...]:
    labels = (
        ("1", "budget.revenue", "Доходы, всего"),
        ("2", "budget.expenditure", "Расходы, всего"),
        ("3", "budget.balance", "Дефицит (-)/Профицит (+)"),
    )
    current = []
    previous = []
    for code, metric_id, label in labels:
        row = _row(flake, code, label)
        current.append(_number(row.values[index]))
        previous.append(_number(row.values[prior_index]) if prior_index is not None else None)
    if any(item is None for item in current):
        raise ValueError("minfin.summary.missing_headline_value")
    if abs(exact_difference(current[2], exact_difference(current[1], current[0]))) > Decimal("0.05"):
        raise ValueError("minfin.summary.inconsistent_budget_totals")
    if all(x is not None for x in previous) and abs(exact_difference(previous[2], exact_difference(previous[1], previous[0]))) > Decimal("0.05"):
        raise ValueError("minfin.summary.inconsistent_budget_totals")
    return tuple(_metric(metric_id, label, now, prev)
                 for (_, metric_id, label), now, prev in zip(labels, current, previous))


def nwf_metrics(flake: FlakeTable, index: int, prior_index: int | None) -> tuple[HeadlineMetric, ...]:
    total = _row(flake, "2", "Объем на конец периода")
    other = _row(flake, "5", "Размещено в иные разрешенные активы на конец периода")
    now_total = _number(total.values[index])
    now_other = _number(other.values[index])
    prev_total = _number(total.values[prior_index]) if prior_index is not None else None
    prev_other = _number(other.values[prior_index]) if prior_index is not None else None
    if now_total is None or now_other is None:
        raise ValueError("minfin.summary.missing_headline_value")
    if now_total < 0 or now_other < 0 or now_other > now_total:
        raise ValueError("minfin.summary.invalid_nwf_balance")
    if prev_total is not None and prev_other is not None and (
        prev_total < 0 or prev_other < 0 or prev_other > prev_total
    ):
        raise ValueError("minfin.summary.invalid_nwf_balance")
    return (
        _metric("nwf.total", "Объем ФНБ на конец периода", now_total, prev_total),
        _metric("nwf.liquid", "Ликвидные активы ФНБ", exact_difference(now_other, now_total),
                exact_difference(prev_other, prev_total) if prev_total is not None and prev_other is not None else None),
    )


def summarize(request: SummaryRequest, profile: HeadlineProfile) -> HeadlineSummary:
    """Profile binding selects a calculation without family-ID switches."""
    flake = request.flake
    expected_unit = "mixed" if profile.profile_id == "minfin.nwf_headlines" else "billion_rub"
    if flake.unit_hint != expected_unit:
        raise ValueError("minfin.summary.unit_mismatch")
    if flake.value_basis not in profile.accepted_basis or flake.frequency not in profile.periods:
        raise ValueError("minfin.summary.incompatible_basis")
    if (flake.frequency == "annual") != (flake.value_basis == "annual"):
        raise ValueError("minfin.summary.incompatible_basis")
    periods = [col.period_id for col in flake.columns]
    if len(set(periods)) != len(periods) or not periods:
        raise ValueError("minfin.summary.invalid_periods")
    target = request.period_id or periods[-1]
    if target not in periods:
        raise ValueError("minfin.summary.period_unavailable")
    index = periods.index(target)
    prior = preceding_year(target)
    prior_index = periods.index(prior) if prior in periods else None
    metrics = profile.calculator(flake, index, prior_index)
    return HeadlineSummary(flake.family_id, flake.source_id, target, flake.frequency,
                           flake.value_basis, flake.original_identity, flake.method_version, metrics,
                           profile.profile_id, profile.method_version,
                           serialize_flake(SerializeFlakeRequest(flake)).identity, flake.publication)


__all__ = ("summarize", "budget_metrics", "nwf_metrics")