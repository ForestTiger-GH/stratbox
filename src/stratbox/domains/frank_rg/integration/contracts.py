from dataclasses import dataclass
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot
from ..tables.contracts import SemanticFlake


@dataclass(frozen=True, slots=True)
class IntegrateRequest:
    flake: SemanticFlake
    dataset_id: str
    release_id: str


@dataclass(frozen=True, slots=True)
class AlignRequest:
    batches: tuple[ObservationBatch, ...]
    dataset_id: str
    release_id: str


@dataclass(frozen=True, slots=True)
class HistoryRequest:
    batches: tuple[ObservationBatch, ...]
    dataset_id: str
    release_id: str


@dataclass(frozen=True, slots=True)
class ObservationSnapshotRequest:
    batch: ObservationBatch
    dataset_id: str | None = None
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadObservationsRequest:
    snapshot: DatasetSnapshot
