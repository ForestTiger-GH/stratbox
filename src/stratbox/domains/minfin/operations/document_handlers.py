from stratbox.core.formats.documents import extract_document as extract_blocks
from stratbox.shared.data.documents import readable_document
from ..documents.contracts import PublisherDocument
from ..documents.snapshots import snapshot_document, document_from_dataset
from ..publications.catalog import family
from . import document_definitions as D
from .pipeline_handlers import _execute


def extract_document(request, *, context=None):
    # The common execution adapter records the exact result; source input remains
    # explicit even for a caller-supplied publication context.
    def build(req, invocation):
        series = family(req.family_id).source(req.publication.series_id)
        if series.kind != "document" or req.payload.source_id not in {None, series.source_id}:
            raise ValueError("minfin.document.source_mismatch")
        doc = extract_blocks(req.payload, series_id=series.source_id, issue_id=req.publication.issue_id,
                             asset_id=req.publication.asset_id, profile_id="minfin.document.blocks",
                             budget=invocation.budget, checkpoint=invocation.check_cancelled)
        if doc.format not in {"pdf", "docx"}:
            raise ValueError("minfin.document.format_unsupported")
        return PublisherDocument(req.family_id, doc, req.publication)
    return _execute(D.EXTRACT_DOCUMENT, request, build, context=context, with_invocation=True)


def build_document_snapshot(request, *, context=None):
    return _execute(D.DOCUMENT_SNAPSHOT_DEF, request,
        lambda r: snapshot_document(r.document, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_document(request, *, context=None):
    return _execute(D.READ_DOCUMENT, request, lambda r: document_from_dataset(r.snapshot), context=context)


def render_document(request, *, context=None):
    return _execute(D.RENDER_DOCUMENT, request, lambda r: readable_document(r.document.document), context=context)
