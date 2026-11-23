"""Reviewed row bindings declare economic meaning independently of cell layout."""
from dataclasses import dataclass

from stratbox.shared.data.observations import MetricRef, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.snapshots import DatasetSnapshot
from ..tables.contracts import FlakeTable


@dataclass(frozen=True, slots=True)
class RowBinding:
    code: str
    metric: MetricRef
    subject: SubjectRef
    perimeter: str
    value_basis: str
    dimensions: tuple[tuple[str, str], ...] = ()
    periods: tuple[tuple[str, PeriodRef], ...] = ()


@dataclass(frozen=True, slots=True)
class IntegrateRequest:
    flake: FlakeTable
    dataset_id: str
    release_id: str
    bindings: tuple[RowBinding, ...] = ()


@dataclass(frozen=True, slots=True)
class ObservationSnapshotRequest:
    batch: ObservationBatch
    dataset_id: str | None = None
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadObservationsRequest:
    snapshot: DatasetSnapshot
