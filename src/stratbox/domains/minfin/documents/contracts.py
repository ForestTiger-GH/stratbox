from dataclasses import dataclass
from stratbox.shared.data.documents import DocumentExtract
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import SourcePayload
from ..publications.context import PublicationContext


@dataclass(frozen=True, slots=True)
class ExtractDocumentRequest:
    family_id: str
    payload: SourcePayload
    publication: PublicationContext


@dataclass(frozen=True, slots=True)
class PublisherDocument:
    family_id: str
    document: DocumentExtract
    publication: PublicationContext


@dataclass(frozen=True, slots=True)
class DocumentSnapshotRequest:
    document: PublisherDocument
    dataset_id: str | None = None
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadDocumentRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True, slots=True)
class RenderDocumentRequest:
    document: PublisherDocument
