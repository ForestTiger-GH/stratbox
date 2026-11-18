"""Calendar period anchors are reproducible without pandas."""

from __future__ import annotations

from datetime import date

import pytest

from stratbox.shared.time.periods import PeriodSpec, period_points, period_spec_points


def test_leap_month_and_quarter_endpoints():
    assert period_points("M", "2024-01-01", "2024-03-31", "end") == [
        date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)]
    assert period_points("Q", "2024-01-01", "2024-12-31", "end") == [
        date(2024, 3, 31), date(2024, 6, 30), date(2024, 9, 30), date(2024, 12, 31)]


def test_partial_period_filters_and_step():
    assert period_points("M", "2024-01-15", "2024-03-31", "start") == [
        date(2024, 2, 1), date(2024, 3, 1)]
    assert period_spec_points(PeriodSpec("M", "end", 2), "2024-01-01", "2024-05-31") == [
        date(2024, 1, 31), date(2024, 3, 31), date(2024, 5, 31)]


def test_iso_weeks_and_year_boundary():
    assert period_points("W", "2024-04-01", "2024-04-07", "start") == [date(2024, 4, 1)]
    assert period_points("W", "2024-04-01", "2024-04-07", "end") == [date(2024, 4, 7)]
    assert period_points("Y", "2023-11-01", "2024-12-31", "end") == [
        date(2023, 12, 31), date(2024, 12, 31)]


def test_calendar_limit_does_not_overflow():
    assert period_points("Y", date.max, date.max, "end") == [date.max]
    assert period_points("W", date.max, date.max, "end") == [date.max]


@pytest.mark.parametrize("args", [
    ("X", "2024-01-01", "2024-12-31"),
    ("M", "2024-01-01", "2024-12-31", "unknown"),
    ("M", "2024-01-01", "2024-12-31", "start", 0),
    ("M", "2024-05-01", "2024-01-01"),
])
def test_invalid_periods_raise(args):
    with pytest.raises(ValueError):
        period_points(*args)
