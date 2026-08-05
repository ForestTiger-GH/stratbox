from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True, slots=True)
class PublicationInterval:
    lower: float
    upper: float


@dataclass(frozen=True, slots=True)
class RoundingPolicy:
    step: float = 1.0
    tolerance: float = 1e-8

    def interval(self, value: float) -> PublicationInterval:
        half = self.step / 2.0
        return PublicationInterval(max(0.0, float(value) - half), float(value) + half)

    def bucket(self, value: float) -> float:
        if value < 0:
            raise ValueError('Published SORS values cannot be negative')
        return floor(float(value) / self.step + 0.5 + self.tolerance) * self.step

    def single_bucket(self, lower: float, upper: float) -> float | None:
        if upper < lower - self.tolerance:
            return None
        lo = self.bucket(max(0.0, lower))
        hi_probe = max(lower, upper - self.tolerance)
        hi = self.bucket(max(0.0, hi_probe))
        return lo if abs(lo - hi) <= self.tolerance else None


def publication_interval(value: float, step: float = 1.0) -> tuple[float, float]:
    x = RoundingPolicy(step=step).interval(value)
    return x.lower, x.upper


def published_bucket(lower: float, upper: float, step: float = 1.0, tol: float = 1e-8) -> float | None:
    return RoundingPolicy(step=step, tolerance=tol).single_bucket(lower, upper)
