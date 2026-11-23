from dataclasses import dataclass

from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.views import ObservationView
from ..analytics.contracts import HeadlineSummary


@dataclass(frozen=True, slots=True)
class PrepareHeadlineViewRequest:
    summary: HeadlineSummary
    view_id: str
    metric_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewSnapshotRequest:
    view: ObservationView
    dataset_id: str | None = None
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadViewRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True, slots=True)
class RenderViewRequest:
    view: ObservationView
    format: str = "csv"
