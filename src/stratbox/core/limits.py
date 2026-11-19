"""Resource limits shared by one operation and its nested readers and writers."""

from __future__ import annotations

from dataclasses import dataclass, fields
from math import inf, isfinite
from time import monotonic
from typing import Callable, Literal

from stratbox.shared.identity import ByteIdentity

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
        self._output_units: dict[str, tuple[ByteIdentity, str | None]] = {}

    def seconds_left(self) -> float:
        return inf if self._deadline == inf else max(0, self._deadline - self._now())

    def checkpoint(self) -> None:
        # No configured deadline means no clock dependency for budget checks.
        if self._deadline != inf and self.seconds_left() <= 0:
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

    def account_output(
        self, key: str, identity: ByteIdentity, *, covered_by: str | None = None,
        completed: bool = False,
    ) -> None:
        """Account one logical output obligation, independently of effect receipts.

        A duplicate key is idempotent only for the same bytes and explicit
        coverage relation. Independent destinations need independent keys,
        even if their bytes match. Coverage is an explicit caller claim,
        not something inferred from an effect kind or a matching digest.
        """
        if not isinstance(key, str) or not 0 < len(key) <= 128 or (
            covered_by is not None and
            (not isinstance(covered_by, str) or not 0 < len(covered_by) <= 128)
        ):
            raise ValueError("Invalid output unit key")
        if not isinstance(identity, ByteIdentity):
            raise ValueError("Invalid output identity")
        target = (identity, covered_by)
        existing = self._output_units.get(key)
        if existing is not None:
            # The runner checks "returned" without knowing whether the
            # handler already explicitly linked it to a publishing unit.
            if existing[0] != identity or (
                covered_by is not None and existing[1] != covered_by
            ):
                raise ValueError("Conflicting output accounting claim")
            return
        if covered_by is not None:
            covered = self._output_units.get(covered_by)
            if covered is None or covered[0] != identity or covered_by == key:
                raise ValueError("Output coverage claim is unsubstantiated")
        else:
            # Complete representations are already computed. The bytes
            # ceiling still applies even when the deadline has passed.
            self.charge("output_bytes", identity.size, completed=completed)
        self._output_units[key] = target

    def output_accounting(self) -> tuple[tuple[str, ByteIdentity, str | None], ...]:
        return tuple((key, identity, covered_by)
                     for key, (identity, covered_by) in self._output_units.items())
