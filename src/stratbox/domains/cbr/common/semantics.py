"""Explicit source coordinate mappings and interpretation diagnostics."""
from dataclasses import dataclass
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef


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
class TableDiagnostic:
    code: str
    sheet: str
    coordinate: str | None = None
    detail: str | None = None
