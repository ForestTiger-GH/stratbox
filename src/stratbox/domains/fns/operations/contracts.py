"""Typed requests for independent FNS boundaries and explicit compositions."""
from dataclasses import dataclass

from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import AcquisitionReceipt, SourcePayload

from ..analytics.calculations import Calculation
from ..integration.contracts import FnsDataset
from ..products.views import PreparedView
from ..publications.contracts import ReleaseContext
from ..tables.contracts import JsonFlake, SourceProjection
from ..tables.legal_entities.extraction import WorkbookBundle


@dataclass(frozen=True, slots=True)
class ExtractRequest:
    payload: SourcePayload
    release: ReleaseContext


@dataclass(frozen=True, slots=True)
class FlakeRequest:
    flake: JsonFlake | WorkbookBundle


@dataclass(frozen=True, slots=True)
class ProjectionRequest:
    projection: SourceProjection


@dataclass(frozen=True, slots=True)
class DatasetRequest:
    dataset: FnsDataset


@dataclass(frozen=True, slots=True)
class CalculationRequest:
    calculation: Calculation


@dataclass(frozen=True, slots=True)
class ViewValueRequest:
    view: PreparedView


@dataclass(frozen=True, slots=True)
class SnapshotRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True, slots=True)
class CompareFlakesRequest:
    before: JsonFlake | WorkbookBundle
    after: JsonFlake | WorkbookBundle


@dataclass(frozen=True, slots=True)
class CompareDatasetsRequest:
    before: FnsDataset
    after: FnsDataset


@dataclass(frozen=True, slots=True)
class ChangesRequest:
    before: FnsDataset
    after: FnsDataset
    metric_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SharesRequest:
    dataset: FnsDataset
    numerator_metric: str
    denominator_metric: str
    numerator_dimensions: tuple[tuple[str, str], ...] = ()
    denominator_dimensions: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ViewRequest:
    dataset: FnsDataset | Calculation
    metric_ids: tuple[str, ...] = ()
    subject_ids: tuple[str, ...] = ()
    period_kinds: tuple[str, ...] = ()
    dimensions: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class RenderRequest:
    view: PreparedView
    format: str = "csv"


@dataclass(frozen=True, slots=True)
class ProcessRequest:
    payload: SourcePayload
    release: ReleaseContext
    format: str = "csv"


@dataclass(frozen=True, slots=True)
class CaptureFullRequest:
    release: ReleaseContext
    url: str | None = None
    format: str = "csv"


@dataclass(frozen=True, slots=True)
class ProcessedRelease:
    flake: JsonFlake | WorkbookBundle
    projection: SourceProjection
    dataset: FnsDataset
    view: PreparedView
    representation: Representation
    original: SourcePayload
    acquisition: AcquisitionReceipt | None = None
