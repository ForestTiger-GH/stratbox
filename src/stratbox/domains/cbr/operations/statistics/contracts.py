"""Explicit operation inputs; no hidden acquisition, destination or selection."""
from dataclasses import dataclass
from stratbox.shared.data.observations import PeriodRef
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
from stratbox.domains.cbr.integration.statistics.contracts import ColumnPeriodBinding, RowBinding, StatisticsDataset
from stratbox.domains.cbr.products.statistics.views import StatisticsView


@dataclass(frozen=True, slots=True)
class ExtractWorkbookRequest:
    original: IdentifiedOriginal


@dataclass(frozen=True, slots=True)
class FlakeRequest:
    flake: WorkbookFlake


@dataclass(frozen=True, slots=True)
class CompareWorkbooksRequest:
    before: WorkbookFlake
    after: WorkbookFlake


@dataclass(frozen=True, slots=True)
class ReadSnapshotRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True, slots=True)
class AlignStatisticsRequest:
    flakes: tuple[WorkbookFlake, ...]
    row_bindings: tuple[RowBinding, ...] = ()
    period_bindings: tuple[ColumnPeriodBinding, ...] = ()
    mapping_version: str = "cbr.source_labels.v1"
    strict: bool = False


@dataclass(frozen=True, slots=True)
class DatasetRequest:
    dataset: StatisticsDataset


@dataclass(frozen=True, slots=True)
class CalculateChangeRequest:
    dataset: StatisticsDataset
    before: PeriodRef
    after: PeriodRef
    method: str = "absolute"
    release_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CalculateShareRequest:
    dataset: StatisticsDataset
    numerator_metric: str
    denominator_metric: str
    release_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BuildViewRequest:
    dataset: StatisticsDataset
    series_ids: tuple[str, ...] = ()
    metric_ids: tuple[str, ...] = ()
    release_ids: tuple[str, ...] = ()
    title: str = "Bank of Russia statistics"


@dataclass(frozen=True, slots=True)
class ViewRequest:
    view: StatisticsView


@dataclass(frozen=True, slots=True)
class RenderViewRequest:
    view: StatisticsView
    format: str = "xlsx"
