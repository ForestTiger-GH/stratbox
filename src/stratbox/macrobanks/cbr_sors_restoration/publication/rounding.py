from __future__ import annotations

from dataclasses import dataclass
from math import floor, inf, isfinite

import numpy as np


@dataclass(frozen=True, slots=True)
class PublicationInterval:
    lower: float
    upper: float
    lower_attained: bool = True
    upper_attained: bool = False

    def __post_init__(self) -> None:
        if self.upper < self.lower:
            raise ValueError(f'Invalid interval [{self.lower}, {self.upper}]')

    @property
    def width(self) -> float:
        return float(self.upper - self.lower)

    @property
    def is_point(self) -> bool:
        return self.lower == self.upper and self.lower_attained and self.upper_attained


@dataclass(frozen=True, slots=True)
class RoundingPolicy:
    step: float = 1.0
    tolerance: float = 1e-8

    def __post_init__(self) -> None:
        if self.step <= 0:
            raise ValueError('Rounding step must be positive')
        if self.tolerance <= 0:
            raise ValueError('Rounding tolerance must be positive')

    def interval(self, value: float) -> PublicationInterval:
        value = float(value)
        if value < 0:
            raise ValueError('Published SORS values cannot be negative')
        half = self.step / 2.0
        return PublicationInterval(
            lower=max(0.0, value - half),
            upper=value + half,
            lower_attained=True,
            upper_attained=False,
        )

    def bucket(self, value: float) -> float:
        value = float(value)
        if value < -self.tolerance:
            raise ValueError('Published SORS values cannot be negative')
        value = max(0.0, value)
        return floor(value / self.step + 0.5) * self.step

    def single_bucket_interval(self, interval: PublicationInterval) -> float | None:
        if interval.upper < interval.lower - self.tolerance:
            return None
        if not (isfinite(interval.lower) and isfinite(interval.upper)):
            return None
        lower_value = max(0.0, float(interval.lower))
        upper_value = max(0.0, float(interval.upper))
        lower_index = floor(lower_value / self.step + 0.5)
        upper_scaled = upper_value / self.step + 0.5
        nearest = round(upper_scaled)
        if not interval.upper_attained and abs(upper_scaled - nearest) <= self.tolerance:
            upper_index = int(nearest) - 1
        else:
            upper_index = floor(upper_scaled)
        return float(lower_index) * self.step if lower_index == upper_index else None

    def single_bucket(
        self,
        lower: float,
        upper: float,
        *,
        lower_attained: bool = True,
        upper_attained: bool = True,
    ) -> float | None:
        return self.single_bucket_interval(
            PublicationInterval(
                float(lower),
                float(upper),
                lower_attained=lower_attained,
                upper_attained=upper_attained,
            )
        )


def publication_interval(value: float, step: float = 1.0) -> PublicationInterval:
    return RoundingPolicy(step=step).interval(value)


def published_bucket(
    lower: float,
    upper: float,
    step: float = 1.0,
    tol: float = 1e-8,
    *,
    lower_attained: bool = True,
    upper_attained: bool = True,
) -> float | None:
    return RoundingPolicy(step=step, tolerance=tol).single_bucket(
        lower,
        upper,
        lower_attained=lower_attained,
        upper_attained=upper_attained,
    )


def solver_lower_bound(value: float, attained: bool, *, open_margin: float = 0.0) -> float:
    value = float(value)
    if attained or not isfinite(value):
        return value
    if open_margin < 0:
        raise ValueError('open_margin cannot be negative')
    adjacent = float(np.nextafter(value, inf))
    return max(adjacent, value + float(open_margin))


def solver_upper_bound(value: float, attained: bool, *, open_margin: float = 0.0) -> float:
    value = float(value)
    if attained or not isfinite(value):
        return value
    if open_margin < 0:
        raise ValueError('open_margin cannot be negative')
    adjacent = float(np.nextafter(value, -inf))
    return min(adjacent, value - float(open_margin))
