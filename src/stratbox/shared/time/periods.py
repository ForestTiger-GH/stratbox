"""Pure calendar anchor generation for Y/Q/M/W/D periods."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
from typing import Literal

Freq = Literal["Y", "Q", "M", "W", "D"]
Anchor = Literal["start", "end"]
_VALID_FREQ = frozenset({"Y", "Q", "M", "W", "D"})
_VALID_ANCHOR = frozenset({"start", "end"})


@dataclass(frozen=True)
class PeriodSpec:
    freq: Freq
    anchor: Anchor = "start"
    step: int = 1

    def __post_init__(self) -> None:
        _validate(self.freq, self.anchor, self.step)


def _validate(freq: str, anchor: str, step: int) -> None:
    if freq not in _VALID_FREQ:
        raise ValueError(f"Unknown freq: {freq}")
    if anchor not in _VALID_ANCHOR:
        raise ValueError(f"Unknown anchor: {anchor}")
    if type(step) is not int or step < 1:
        raise ValueError("step must be a positive integer")


def _to_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise TypeError("Period boundary must be date, datetime or ISO YYYY-MM-DD string")


def _start(freq: Freq, value: date) -> date:
    if freq == "Y":
        return date(value.year, 1, 1)
    if freq == "Q":
        return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)
    if freq == "M":
        return value.replace(day=1)
    if freq == "W":
        return value - timedelta(days=value.weekday())
    return value


def _end(freq: Freq, value: date) -> date:
    if freq == "Y":
        return date(value.year, 12, 31)
    if freq == "Q":
        month = ((value.month - 1) // 3) * 3 + 3
        return date(value.year, month, calendar.monthrange(value.year, month)[1])
    if freq == "M":
        return date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])
    if freq == "W":
        return value + timedelta(days=6 - value.weekday())
    return value


def _next(freq: Freq, value: date) -> date | None:
    if freq in {"D", "W"}:
        try:
            return value + timedelta(days=1 if freq == "D" else 7)
        except OverflowError:
            return None
    month_step = {"M": 1, "Q": 3, "Y": 12}[freq]
    month_index = value.year * 12 + value.month - 1 + month_step
    year, month0 = divmod(month_index, 12)
    return date(year, month0 + 1, 1) if year <= 9999 else None


def period_points(freq: Freq, date_from: str | date | datetime,
                  date_to: str | date | datetime | None = None,
                  anchor: Anchor = "start", step: int = 1) -> list[date]:
    """Include only period anchor dates inside [date_from, date_to].

    The default upper boundary is today's local calendar date. Pass date_to for
    reproducible calculations; this operation never checks period overlap.
    """
    _validate(freq, anchor, step)
    lower = _to_date(date_from)
    upper = _to_date(date_to) if date_to is not None else date.today()
    if lower > upper:
        raise ValueError("date_from must not exceed date_to")
    current = _start(freq, lower)
    values: list[date] = []
    index = 0
    while current <= upper:
        if index % step == 0:
            point = current if anchor == "start" else _end(freq, current)
            if lower <= point <= upper:
                values.append(point)
        following = _next(freq, current)
        if following is None:
            break
        current = following
        index += 1
    return values


def period_spec_points(spec: PeriodSpec, date_from: str | date | datetime,
                       date_to: str | date | datetime | None = None) -> list[date]:
    return period_points(spec.freq, date_from, date_to, spec.anchor, spec.step)
