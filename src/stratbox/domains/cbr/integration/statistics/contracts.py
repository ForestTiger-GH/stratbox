"""Source-versioned observation batches; mapping is independent of storage."""
from dataclasses import dataclass
from stratbox.shared.data.observations import MetricRef, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.cbr.tables.statistics.contracts import TableDiagnostic


@dataclass(frozen=True, slots=True)
class RowBinding:
    series_id: str
    sheet: str
    source_row: int
    metric: MetricRef
    subject: SubjectRef
    dimensions: tuple[tuple[str, str], ...] = ()
    perimeter: str | None = None


@dataclass(frozen=True, slots=True)
class ColumnPeriodBinding:
    series_id: str
    sheet: str
    column: int
    period: PeriodRef


@dataclass(frozen=True, slots=True)
class InputVersion:
    series_id: str
    issue_id: str
    original: ByteIdentity
    flake: ByteIdentity
    profile_id: str
    profile_version: int
    asset_id: str = "main"


@dataclass(frozen=True, slots=True)
class StatisticsDataset:
    batches: tuple[ObservationBatch, ...]
    inputs: tuple[InputVersion, ...]
    mapping_version: str
    diagnostics: tuple[TableDiagnostic, ...] = ()
    method: str = "source_alignment_v1"

    @property
    def lineage(self) -> tuple[UsedInputReceipt, ...]:
        return tuple(dict.fromkeys(receipt for batch in self.batches for receipt in batch.lineage))

    @property
    def identity(self):
        from .snapshots import dataset_snapshot
        return dataset_snapshot(self).identity
