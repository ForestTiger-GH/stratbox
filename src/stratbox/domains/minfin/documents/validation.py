"""Source-context and physical-document validation without economic inference."""
from .contracts import PublisherDocument, DocumentValidation
from .snapshots import snapshot_document
from ..publications.catalog import family


def validate_document(value):
    if not isinstance(value, PublisherDocument):
        raise ValueError("minfin.document.publisher_document_required")
    source = family(value.family_id).source(value.publication.series_id)
    if source.kind != "document":
        raise ValueError("minfin.document.source_mismatch")
    # Canonical snapshot construction checks ordered geometry, exact publication
    # coordinates, lineage and source identity without acquiring any material.
    snapshot_document(value)
    document = value.document
    findings = tuple("block:"+str(block.ordinal)+":extraction_failed" for block in document.blocks if block.kind == "error")
    text_characters = sum(len(block.text)+sum(len(cell) for row in block.rows for cell in row) for block in document.blocks)
    if not text_characters:
        findings += ("document.no_text_or_cell_content",)
    return DocumentValidation(value.family_id, source.source_id, len(document.blocks),
        sum(block.kind == "table" for block in document.blocks),
        sum(len(row) for block in document.blocks for row in block.rows), text_characters,
        findings, document.coverage.status)
