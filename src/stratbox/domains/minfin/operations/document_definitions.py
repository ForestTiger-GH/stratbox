from stratbox.core.execution import InputPort, OperationDefinition, OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.execution.semantics import ProcessingFunction
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.representation import Representation
from ..documents.contracts import ExtractDocumentRequest, PublisherDocument, DocumentSnapshotRequest, ReadDocumentRequest, RenderDocumentRequest
from ..documents.snapshots import DOCUMENT_SNAPSHOT

_DOCUMENT = DataContract("minfin.publisher_document", 1, DataRole.EXTRACTS)
EXTRACT_DOCUMENT = OperationDefinition("minfin.extract_document", 1, "minfin.document.blocks.v1", ExtractDocumentRequest, PublisherDocument,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("payload", DataContract("source.payload", 1, DataRole.ORIGINALS), "payload"),),
        outputs=(OutputPort("document", _DOCUMENT),), parameters=("family_id", "publication"),
        summary="Extract ordered PDF or DOCX blocks under explicit publisher release context; document geometry remains qualified."))
DOCUMENT_SNAPSHOT_DEF = OperationDefinition("minfin.document_snapshot", 1, "minfin.document.snapshot.v1", DocumentSnapshotRequest, DatasetSnapshot,
    processing=OperationSemantics((), function=ProcessingFunction.ENCODE,
        inputs=(InputPort("document", _DOCUMENT, "document"),),
        outputs=(OutputPort("snapshot", DOCUMENT_SNAPSHOT), OutputPort("dataset", DataContract("dataset.snapshot", 1))),
        parameters=("dataset_id", "version_id"), summary="Retain ordered document evidence and complete publisher context in a portable dataset."))
READ_DOCUMENT = OperationDefinition("minfin.read_document", 1, "minfin.document.snapshot.v1", ReadDocumentRequest, PublisherDocument,
    processing=OperationSemantics((), function=ProcessingFunction.REPLAY,
        inputs=(InputPort("snapshot", DOCUMENT_SNAPSHOT, "snapshot"),), outputs=(OutputPort("document", _DOCUMENT),),
        summary="Replay retained publisher document blocks and release evidence without the document decoder."))
RENDER_DOCUMENT = OperationDefinition("minfin.render_document", 1, "minfin.document.readable.v1", RenderDocumentRequest, Representation,
    processing=OperationSemantics((ProcessingStage.READABLE,), inputs=(InputPort("document", _DOCUMENT, "document"),),
        outputs=(OutputPort("representation", DataContract("document.readable.jsonl", 1, DataRole.READABLE)),),
        summary="Render retained ordered document blocks as source-qualified JSONL for downstream reading."))
