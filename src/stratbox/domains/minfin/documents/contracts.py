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


@dataclass(frozen=True, slots=True)
class DocumentValidation:
    family_id: str
    source_id: str
    blocks: int
    tables: int
    cells: int
    text_characters: int
    findings: tuple[str, ...]
    coverage_status: str
    level: str = "physical_structure_only"

    @property
    def valid(self):
        return not self.findings
