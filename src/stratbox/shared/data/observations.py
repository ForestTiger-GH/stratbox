from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


_VALUE_STATUSES = frozenset({
    "reported", "blank", "dash", "missing", "not_applicable",
    "withheld", "derived", "reconstructed",
})

ValueStatus = Literal[
    "reported",
    "blank",
    "dash",
    "missing",
    "not_applicable",
    "withheld",
    "derived",
    "reconstructed",
]


@dataclass(frozen=True, slots=True)
class SubjectRef:
    namespace: str
    id: str


@dataclass(frozen=True, slots=True)
class MetricRef:
    id: str
    unit: str
    quantity_kind: Literal["stock", "flow", "ratio", "index", "count"] | None = None
    definition_id: str | None = None
    scale: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Metric identity must be nonempty")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("Metric unit must be nonempty")
        if self.quantity_kind is not None and self.quantity_kind not in {
            "stock", "flow", "ratio", "index", "count"
        }:
            raise ValueError("Invalid metric quantity kind")
        if self.definition_id is not None and (
            not isinstance(self.definition_id, str) or not self.definition_id.strip()
        ):
            raise ValueError("Metric definition identity must be nonempty if supplied")
        if self.scale is not None and type(self.scale) is not Decimal:
            raise TypeError("Metric scale must be a Decimal")
        if self.scale is not None and (not self.scale.is_finite() or self.scale <= 0):
            raise ValueError("Invalid measurement scale")


@dataclass(frozen=True, slots=True)
class PeriodRef:
    kind: Literal["capture", "as_of", "interval"]
    as_of: date | None = None
    start: date | None = None
    end: date | None = None

    def __post_init__(self) -> None:
        if self.kind == "interval":
            valid = (
                self.as_of is None
                and self.start is not None
                and self.end is not None
                and self.start <= self.end
            )
        else:
            valid = (
                self.kind in {"capture", "as_of"}
                and self.as_of is not None
                and self.start is self.end is None
            )
        if not valid:
            raise ValueError("Invalid observation period")


@dataclass(frozen=True, slots=True)
class Observation:
    subject: SubjectRef
    metric: MetricRef
    period: PeriodRef
    dimensions: tuple[tuple[str, str], ...]
    perimeter: str
    value: int | Decimal | str | None
    value_status: ValueStatus
    evidence_ref: str
    raw_token: str | None = None

    def __post_init__(self) -> None:
        if self.value_status not in _VALUE_STATUSES:
            raise ValueError("Unknown observation value status")
        if self.value is not None and (
            type(self.value) not in (int, str, Decimal)
        ):
            raise TypeError("Observation value must be int, Decimal, str or None")
        if self.raw_token is not None and not isinstance(self.raw_token, str):
            raise TypeError("Raw observation token must be text when present")
        if (self.value_status in {"reported", "derived", "reconstructed"}) != (self.value is not None):
            raise ValueError("Observation value disagrees with its status")
        if isinstance(self.value, Decimal) and not self.value.is_finite():
            raise ValueError("Observation requires a finite value")
        if len({key for key, _ in self.dimensions}) != len(self.dimensions):
            raise ValueError("Duplicate observation dimension")
