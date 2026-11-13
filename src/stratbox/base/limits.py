"""Resource limits shared by one operation and its nested readers and writers."""

from __future__ import annotations

from dataclasses import dataclass, fields
from math import inf, isfinite
from time import monotonic
from typing import Callable, Literal

Resource = Literal[
    "input_bytes", "wire_bytes", "decoded_bytes", "output_bytes",
    "requests", "objects", "cells", "temporary_bytes", "archive_depth",
]


class BudgetExceeded(RuntimeError):
    def __init__(self, resource: str):
        self.resource = resource
        self.code = f"budget.{resource}"
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ExecutionBudget:
    seconds: float | None = None
    input_bytes: int | None = None
    wire_bytes: int | None = None
    decoded_bytes: int | None = None
    output_bytes: int | None = None
    requests: int | None = None
    objects: int | None = None
    cells: int | None = None
    temporary_bytes: int | None = None
    archive_depth: int | None = None

    def __post_init__(self):
        for item in fields(self):
            value = getattr(self, item.name)
            if value is None:
                continue
            if item.name == "seconds":
                if type(value) not in (int, float) or not 0 <= value <= 2**53 or not isfinite(value):
                    raise ValueError("Invalid operation deadline")
            elif type(value) is not int or not 0 <= value <= 2**63 - 1:
                raise ValueError(f"Invalid limit for {item.name}")

    @classmethod
    def intersect(cls, *budgets: ExecutionBudget | None) -> ExecutionBudget:
        return cls(**{
            item.name: min(
                (value for budget in budgets if budget is not None
                 if (value := getattr(budget, item.name)) is not None),
                default=None,
            )
            for item in fields(cls)
        })


class BudgetMeter:
    """Cumulative resources and a monotonic deadline for one invocation."""

    def __init__(
        self, limits: ExecutionBudget, *, now: Callable[[], float] = monotonic
    ):
        self.limits = limits
        self._now = now
        self._deadline = now() + limits.seconds if limits.seconds is not None else inf
        self._used: dict[Resource, int] = {}

    def seconds_left(self) -> float:
        return max(0, self._deadline - self._now())

    def checkpoint(self) -> None:
        if self.seconds_left() <= 0:
            raise BudgetExceeded("deadline")

    def used(self, resource: Resource) -> int:
        return self._used.get(resource, 0)

    def usage(self) -> tuple[tuple[Resource, int], ...]:
        return tuple(sorted(self._used.items()))

    def remaining(self, resource: Resource) -> int | None:
        limit = getattr(self.limits, resource)
        return None if limit is None else limit - self.used(resource)

    def check(self, resource: Resource, amount: int, *, completed: bool = False) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("Invalid resource charge")
        if not completed:
            self.checkpoint()
        remaining = self.remaining(resource)
        if remaining is not None and amount > remaining:
            raise BudgetExceeded(resource)

    def charge(self, resource: Resource, amount: int, *, completed: bool = False) -> None:
        self.check(resource, amount, completed=completed)
        self._used[resource] = self.used(resource) + amount
