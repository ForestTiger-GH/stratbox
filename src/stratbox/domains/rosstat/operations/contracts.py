"""Typed domain requests; importing these does not load optional engines."""
from dataclasses import dataclass
from stratbox.core.formats.archives.members import ArchiveLimits
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.data.documents import DocumentExtract
from stratbox.shared.data.views import ObservationView
from ..publications.contracts import RosstatPublicationIndex
from ..publications.archives import RegionalArchiveInventory
from ..publications.discovery.approval import ReviewedIndexScope
from ..tables.contracts import RosstatSourceFlake,ReviewedTableProfile
from ..tables.documents import ReviewedDocumentLayout
from ..integration.datasets import RosstatDataset

@dataclass(frozen=True,slots=True)
class SelectRequest:
    index: RosstatPublicationIndex
    issue_ids: tuple[str,...]=()
    asset_roles: tuple[str,...]=("primary",)
    policy: str="explicit"
    max_assets: int=20

@dataclass(frozen=True,slots=True)
class IndexComparisonRequest:
    before: RosstatPublicationIndex
    after: RosstatPublicationIndex

@dataclass(frozen=True,slots=True)
class ApproveIndexRequest:
    index: RosstatPublicationIndex
    evidence: ReviewedIndexScope

@dataclass(frozen=True,slots=True)
class PhysicalRequest:
    payload: SourcePayload
    series_id: str
    issue_id: str
    asset_id: str
    container_identity: ByteIdentity | None=None
    member: str | None=None

@dataclass(frozen=True,slots=True)
class PayloadRequest:
    payload: SourcePayload
    limits: ArchiveLimits=ArchiveLimits(packed_bytes=256*1024**2,unpacked_bytes=512*1024**2,member_bytes=128*1024**2)

@dataclass(frozen=True,slots=True)
class MembersRequest:
    payload: SourcePayload
    inventory: RegionalArchiveInventory
    names: tuple[str,...]
    limits: ArchiveLimits=ArchiveLimits(packed_bytes=256*1024**2,unpacked_bytes=512*1024**2,member_bytes=128*1024**2)

@dataclass(frozen=True,slots=True)
class WorkbookRequest:
    workbook: WorkbookExtract

@dataclass(frozen=True,slots=True)
class WorkbookComparisonRequest:
    before: WorkbookExtract
    after: WorkbookExtract

@dataclass(frozen=True,slots=True)
class DocumentRequest:
    document: DocumentExtract

@dataclass(frozen=True,slots=True)
class StructureDocumentRequest:
    document: DocumentExtract
    layout: ReviewedDocumentLayout

@dataclass(frozen=True,slots=True)
class MapCellsRequest:
    physical: WorkbookExtract | DocumentExtract
    profile: ReviewedTableProfile

@dataclass(frozen=True,slots=True)
class FlakeRequest:
    flake: RosstatSourceFlake

@dataclass(frozen=True,slots=True)
class SnapshotRequest:
    snapshot: DatasetSnapshot

@dataclass(frozen=True,slots=True)
class IntegrateRequest:
    flakes: tuple[RosstatSourceFlake,...]
    dataset_id: str
    release_id: str

@dataclass(frozen=True,slots=True)
class DatasetRequest:
    dataset: RosstatDataset

@dataclass(frozen=True,slots=True)
class DatasetComparisonRequest:
    before: RosstatDataset
    after: RosstatDataset

@dataclass(frozen=True,slots=True)
class GrowthRequest:
    dataset: RosstatDataset
    release_id: str

@dataclass(frozen=True,slots=True)
class ViewRequest:
    view: ObservationView

@dataclass(frozen=True,slots=True)
class PrepareViewRequest:
    dataset: RosstatDataset
    view_id: str="rosstat.observations"
    metric_ids: tuple[str,...]=()

@dataclass(frozen=True,slots=True)
class RenderViewRequest:
    view: ObservationView
    format: str="csv"

@dataclass(frozen=True,slots=True)
class FlakeComparisonRequest:
    before: RosstatSourceFlake
    after: RosstatSourceFlake
