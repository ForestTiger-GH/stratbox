"""Byte-bound reviewed table regions in publisher document text.

PDF decoding preserves pages first. Turning a page region into rows requires a
reviewed layout pinned to that exact original, with literal separators or fixed
character boundaries; no whitespace heuristic invents cells or their semantics.
"""
from dataclasses import dataclass, replace
from stratbox.shared.data.documents import DocumentBlock,DocumentExtract
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

@dataclass(frozen=True,slots=True)
class DocumentTableRegion:
    block_ordinal: int
    table_id: str
    first_line: int
    last_line: int
    columns: int
    separator: str | None = None
    column_starts: tuple[int,...] = ()

    def __post_init__(self):
        if self.block_ordinal<0 or not self.table_id or self.first_line<1 or self.last_line<self.first_line or self.columns<1:
            raise ValueError("rosstat.document_region_invalid")
        if bool(self.separator) == bool(self.column_starts):
            raise ValueError("rosstat.document_region_layout_required")
        if self.column_starts and (self.column_starts[0] != 0 or len(self.column_starts) != self.columns
                or tuple(sorted(set(self.column_starts))) != self.column_starts):
            raise ValueError("rosstat.document_region_columns_invalid")

@dataclass(frozen=True,slots=True)
class ReviewedDocumentLayout:
    profile_id: str
    version: int
    source_identity: ByteIdentity
    review_evidence: str
    regions: tuple[DocumentTableRegion,...]


def structure_document(document: DocumentExtract, layout: ReviewedDocumentLayout) -> DocumentExtract:
    if document.source_identity != layout.source_identity or not layout.review_evidence or not layout.profile_id or layout.version<1 or not layout.regions:
        raise ValueError("rosstat.document_reviewed_layout_required")
    if len({r.table_id for r in layout.regions}) != len(layout.regions):
        raise ValueError("rosstat.document_table_duplicate")
    blocks=list(document.blocks)
    for region in layout.regions:
        if region.block_ordinal>=len(document.blocks):
            raise ValueError("rosstat.document_region_block_missing")
        source=document.blocks[region.block_ordinal]
        if source.kind not in {"page","paragraph"}:
            raise ValueError("rosstat.document_region_text_required")
        lines=source.text.splitlines()
        if region.last_line>len(lines):
            raise ValueError("rosstat.document_region_outside_source")
        rows=[]
        for line in lines[region.first_line-1:region.last_line]:
            if region.separator is not None:
                row=tuple(line.split(region.separator))
            else:
                ends=(*region.column_starts[1:],len(line))
                if any(start>len(line) for start in region.column_starts):
                    raise ValueError("rosstat.document_region_short_line")
                row=tuple(line[a:b] for a,b in zip(region.column_starts,ends))
            if len(row)!=region.columns:
                raise ValueError("rosstat.document_region_width_mismatch")
            rows.append(row)
        blocks.append(DocumentBlock(len(blocks),"table","\n".join(lines[region.first_line-1:region.last_line]),source.page,
            tuple(rows),region.table_id))
    receipt=UsedInputReceipt("document_text_extract",document.identity,"application/vnd.stratbox.dataset","inline")
    return replace(document,profile_id=layout.profile_id,profile_version=layout.version,blocks=tuple(blocks),
        lineage=(*document.lineage,receipt),coverage=SnapshotCoverage("partial","Original text blocks retained, plus explicitly reviewed table regions: " + ", ".join(r.table_id for r in layout.regions)),
        qualifications=(*document.qualifications,"Reviewed text layout: " + layout.review_evidence))
