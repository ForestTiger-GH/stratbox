
from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.representation import Representation
from ..documents.contracts import ExtractDocumentRequest, PublisherDocument, DocumentSnapshotRequest, ReadDocumentRequest, RenderDocumentRequest
from ..documents.snapshots import DOCUMENT_SNAPSHOT

EXTRACT_DOCUMENT = _registry_definition('minfin.extract_document')
DOCUMENT_SNAPSHOT_DEF = _registry_definition('minfin.document_snapshot')
READ_DOCUMENT = _registry_definition('minfin.read_document')
RENDER_DOCUMENT = _registry_definition('minfin.render_document')
