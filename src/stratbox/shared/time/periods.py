"""
Модуль содержит универсальные функции генерации временных периодов.

Идея:
- Генерируются "опорные даты" периодов (start/end).
- Поддерживаются частоты: год, квартал, месяц, неделя, день.
- Используется в разных задачах (не только macrobanks).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Literal, Optional

import pandas as pd


Freq = Literal["Y", "Q", "M", "W", "D"]
Anchor = Literal["start", "end"]


@dataclass(frozen=True)
class PeriodSpec:
    """
    Описание сетки периодов.

    freq:
      - Y: годы
      - Q: кварталы
      - M: месяцы
      - W: недели (ISO, от понедельника)
      - D: дни
    anchor:
      - start: первая дата периода
      - end: последняя дата периода
    step:
      - шаг периодов (1 = каждый период, 2 = через один и т.д.)
    """
    freq: Freq
    anchor: Anchor = "start"
    step: int = 1


def _to_date(x: str | date | datetime) -> date:
    """
    Приведение входной даты к datetime.date.
    """
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    return pd.Timestamp(x).date()


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _month_end(d: date) -> date:
    # последний день месяца: первый день следующего месяца - 1 день
    nd = (pd.Timestamp(d) + pd.offsets.MonthBegin(1)).date()
    return nd - timedelta(days=1)


def _quarter_start(d: date) -> date:
    q = (d.month - 1) // 3 + 1
    m = 1 + (q - 1) * 3
    return date(d.year, m, 1)


def _quarter_end(d: date) -> date:
    qs = _quarter_start(d)
    # + 3 месяца -> начало следующего квартала - 1 день
    nd = (pd.Timestamp(qs) + pd.offsets.MonthBegin(3)).date()
    return nd - timedelta(days=1)


def _year_start(d: date) -> date:
    return date(d.year, 1, 1)


def _year_end(d: date) -> date:
    return date(d.year, 12, 31)


def _week_start(d: date) -> date:
    # ISO-неделя: понедельник = 0
    return d - timedelta(days=d.weekday())


def _week_end(d: date) -> date:
    return _week_start(d) + timedelta(days=6)


def period_points(
    freq: Freq,
    date_from: str | date | datetime,
    date_to: str | date | datetime | None = None,
    anchor: Anchor = "start",
    step: int = 1,
) -> list[date]:
    """
    Генерирует список опорных дат по периодам.

    Примеры:
      - period_points("M", "2024-01-01", "2024-03-31", anchor="start")
        -> [2024-01-01, 2024-02-01, 2024-03-01]
      - period_points("M", "2024-01-01", "2024-03-31", anchor="end")
        -> [2024-01-31, 2024-02-29, 2024-03-31]
      - period_points("Q", "2024-01-01", "2024-12-31", anchor="end")
        -> [2024-03-31, 2024-06-30, 2024-09-30, 2024-12-31]

    Важно: date_to=None означает "текущая дата" (today).
    """
    if step < 1:
        raise ValueError("step must be >= 1")

    df = _to_date(date_from)
    dt = _to_date(date_to) if date_to is not None else pd.Timestamp.today().date()

    # Нормализуем нижнюю границу на начало периода, чтобы сетка была стабильной
    if freq == "D":
        cur = df
    elif freq == "W":
        cur = _week_start(df)
    elif freq == "M":
        cur = _month_start(df)
    elif freq == "Q":
        cur = _quarter_start(df)
    elif freq == "Y":
        cur = _year_start(df)
    else:
        raise ValueError(f"Unknown freq: {freq}")

    out: list[date] = []
    k = 0

    while cur <= dt:
        if k % step == 0:
            if freq == "D":
                p = cur
            elif freq == "W":
                p = _week_start(cur) if anchor == "start" else _week_end(cur)
            elif freq == "M":
                p = _month_start(cur) if anchor == "start" else _month_end(cur)
            elif freq == "Q":
                p = _quarter_start(cur) if anchor == "start" else _quarter_end(cur)
            else:  # "Y"
                p = _year_start(cur) if anchor == "start" else _year_end(cur)
            if p >= df and p <= dt:
                out.append(p)

        # шаг вперёд на 1 период
        if freq == "D":
            cur = cur + timedelta(days=1)
        elif freq == "W":
            cur = cur + timedelta(days=7)
        elif freq == "M":
            cur = (pd.Timestamp(cur) + pd.offsets.MonthBegin(1)).date()
        elif freq == "Q":
            cur = (pd.Timestamp(cur) + pd.offsets.MonthBegin(3)).date()
        else:  # "Y"
            cur = date(cur.year + 1, 1, 1)

        k += 1

    return out


def period_spec_points(spec: PeriodSpec, date_from: str | date | datetime, date_to: str | date | datetime | None = None) -> list[date]:
    """
    Удобная обёртка для PeriodSpec.
    """
    return period_points(freq=spec.freq, date_from=date_from, date_to=date_to, anchor=spec.anchor, step=spec.step)
