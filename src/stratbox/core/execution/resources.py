"""Atomic session capacity reservations and cumulative resource expenditure."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from types import MappingProxyType
from typing import Mapping

from stratbox.core.limits import BudgetExceeded, BudgetMeter


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    occupied: Mapping[str, int]
    spent: Mapping[str, int]
    peak: Mapping[str, int]
    reservations: int


class ResourceLedger:
    """Reserve a task's complete capacity vector before occupying a worker.

    Capacity is returned by release. Expenditure is irreversible and is charged
    by the invocation's budget meter, never again by parent result summaries.
    """

    def __init__(self, capacities=None, *, expenditure=None, per_origin=2, starvation_seconds=0.1):
        self.capacities = dict(capacities or {})
        self.expenditure = dict(expenditure or {})
        self.per_origin = per_origin
        for limit in (*self.capacities.values(), *self.expenditure.values(), per_origin):
            if type(limit) is not int or limit < 0:
                raise ValueError("resource.invalid_limit")
        self._lock = RLock()
        self._reservations = {}
        self._occupied = {}
        self._spent = {}
        self._peak = {}
        self._waiting = {}
        self.starvation_seconds = starvation_seconds

    def capacity(self, resource):
        if resource in self.capacities:
            return self.capacities[resource]
        if resource.startswith("origin:"):
            return self.per_origin
        if resource.startswith("target:"):
            return 1
        raise ValueError("resource.capacity_unknown")

    def validate(self, requirements):
        for name, amount in requirements.items():
            if not isinstance(name, str) or type(amount) is not int or amount < 0:
                raise ValueError("resource.invalid_reservation")
            if amount > self.capacity(name):
                raise ValueError("resource.unsatisfiable")

    def reserve(self, owner, requirements):
        with self._lock:
            if owner in self._reservations:
                raise ValueError("resource.reservation_exists")
            self.validate(requirements)
            if "worker" not in requirements:
                return self.replace(owner, requirements)
            now = monotonic()
            # An aged multi-unit claim reserves its conflicting capacity vector.
            # Independent resources remain usable while occupied units drain.
            for other, (since, claim) in self._waiting.items():
                if other != owner and now - since >= self.starvation_seconds and any(
                    amount and claim.get(name, 0) for name, amount in requirements.items()
                    if name != "worker"
                ):
                    self._waiting.setdefault(owner, (now, dict(requirements)))
                    return False
            admitted = self.replace(owner, requirements)
            if admitted:
                self._waiting.pop(owner, None)
            else:
                self._waiting.setdefault(owner, (now, dict(requirements)))
            return admitted

    def replace(self, owner, requirements):
        self.validate(requirements)
        with self._lock:
            previous = self._reservations.get(owner, {})
            if any(self._occupied.get(name, 0) - previous.get(name, 0) + amount > self.capacity(name)
                   for name, amount in requirements.items()):
                return False
            for name, amount in previous.items():
                self._occupied[name] -= amount
            self._reservations[owner] = dict(requirements)
            for name, amount in requirements.items():
                self._occupied[name] = self._occupied.get(name, 0) + amount
                self._peak[name] = max(self._peak.get(name, 0), self._occupied[name])
            return True

    def requirements(self, owner):
        with self._lock:
            return dict(self._reservations.get(owner, {}))

    def release(self, owner):
        with self._lock:
            self._waiting.pop(owner, None)
            for name, amount in self._reservations.pop(owner, {}).items():
                self._occupied[name] -= amount

    def check(self, resource, amount):
        if type(amount) is not int or amount < 0:
            raise ValueError("resource.invalid_charge")
        with self._lock:
            limit = self.expenditure.get(resource)
            if limit is not None and self._spent.get(resource, 0) + amount > limit:
                raise BudgetExceeded(resource)

    def charge(self, resource, amount):
        with self._lock:
            self.check(resource, amount)
            self._spent[resource] = self._spent.get(resource, 0) + amount

    def remaining(self, resource):
        with self._lock:
            limit = self.expenditure.get(resource)
            return None if limit is None else limit - self._spent.get(resource, 0)

    def snapshot(self):
        with self._lock:
            return ResourceSnapshot(*(MappingProxyType(dict(value)) for value in
                (self._occupied, self._spent, self._peak)), len(self._reservations))


class SharedBudgetMeter(BudgetMeter):
    """Keep operation accounting and enforce its enclosing session's ceiling."""

    def __init__(self, limits, ledger, **kwargs):
        super().__init__(limits, **kwargs)
        self.ledger = ledger

    def remaining(self, resource):
        limits = [value for value in (super().remaining(resource), self.ledger.remaining(resource))
                  if value is not None]
        return min(limits) if limits else None

    def charge(self, resource, amount, *, completed=False):
        # Local meter is owned by one invocation; the shared debit is atomic.
        self.check(resource, amount, completed=completed)
        self.ledger.charge(resource, amount)
        self._used[resource] = self.used(resource) + amount


class ScopedResourceLedger:
    """An atomic expenditure ceiling inherited by one workflow scope."""

    def __init__(self, parent, expenditure):
        self.parent = parent
        self.expenditure = dict(expenditure)
        if any(type(value) is not int or value < 0 for value in self.expenditure.values()):
            raise ValueError("resource.invalid_limit")
        self._spent = {}
        self._lock = parent._lock

    def check(self, resource, amount):
        with self._lock:
            self.parent.check(resource, amount)
            limit = self.expenditure.get(resource)
            if limit is not None and self._spent.get(resource, 0) + amount > limit:
                raise BudgetExceeded(resource)

    def charge(self, resource, amount):
        with self._lock:
            self.check(resource, amount)
            self.parent.charge(resource, amount)
            self._spent[resource] = self._spent.get(resource, 0) + amount

    def remaining(self, resource):
        with self._lock:
            limit = self.expenditure.get(resource)
            local = None if limit is None else limit - self._spent.get(resource, 0)
            values = [value for value in (local, self.parent.remaining(resource)) if value is not None]
            return min(values) if values else None
