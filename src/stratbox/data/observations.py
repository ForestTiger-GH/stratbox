from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from .evidence import UsedInputReceipt

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
        if (self.value_status in {"reported", "derived", "reconstructed"}) != (self.value is not None):
            raise ValueError("Observation value disagrees with its status")
        if isinstance(self.value, Decimal) and not self.value.is_finite():
            raise ValueError("Observation requires a finite value")
        if len({key for key, _ in self.dimensions}) != len(self.dimensions):
            raise ValueError("Duplicate observation dimension")


@dataclass(frozen=True, slots=True)
class ObservationBatch:
    dataset_id: str
    schema_version: int
    release_id: str
    observations: tuple[Observation, ...]
    lineage: tuple[UsedInputReceipt, ...]
