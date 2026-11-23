"""Bounded PDF text pages and ordered DOCX body blocks, without table inference."""
from __future__ import annotations

from io import BytesIO

from stratbox.core.formats.archives.members import open_zip
from stratbox.core.formats.xml import parse_xml
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.documents import DocumentBlock, DocumentExtract
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


def extract_document(payload: SourcePayload, *, series_id, issue_id, asset_id="main",
                     profile_id="document.blocks.v1", profile_version=1, budget=None, checkpoint=None):
    if not isinstance(payload, SourcePayload) or not 0 < len(payload.data) <= 128 * 1024 * 1024:
        raise ValueError("document.source_size_invalid")

    def check(size=0):
        if budget is not None:
            budget.checkpoint()
            budget.charge("decoded_bytes", size)
        if checkpoint is not None:
            checkpoint()

    blocks, qualifications = [], []
    check()
    if payload.data.startswith(b"%PDF-"):
        pypdf = require_extra("pypdf", "pdf")
        reader = pypdf.PdfReader(BytesIO(payload.data), strict=True)
        if reader.is_encrypted:
            raise ValueError("document.encrypted_pdf")
        if len(reader.pages) > 10000:
            raise ValueError("document.page_limit")
        for ordinal, page in enumerate(reader.pages):
            check()
            try:
                text = page.extract_text() or ""
            except Exception as error:
                # This is page-local evidence loss, retained explicitly in the result.
                blocks.append(DocumentBlock(ordinal, "error", "", ordinal+1, locator=f"page:{ordinal+1}"))
                qualifications.append(f"page:{ordinal+1}:text_extraction_failed:{type(error).__name__}")
                continue
            check(len(text.encode("utf-8")))
            blocks.append(DocumentBlock(ordinal, "page", text, ordinal+1, locator=f"page:{ordinal+1}"))
            if not text.strip():
                qualifications.append(f"page:{ordinal+1}:no_text_layer_extracted")
        fmt = "pdf"
        qualifications.append("PDF text order is decoder order; images, table geometry and OCR are outside this profile.")
        coverage = SnapshotCoverage("partial", "Every page attempted; extracted text only, with explicit failed or empty pages.")
    elif payload.data.startswith(b"PK"):
        # Admit bounded package entries and XML before handing the body to a decoder.
        with open_zip(payload.data, budget=budget) as package:
            if "word/document.xml" not in package.namelist():
                raise ValueError("document.docx_required")
            for name in package.namelist():
                if name.endswith((".xml", ".rels")):
                    raw = package.read(name)
                    check(len(raw))
                    parse_xml(raw)
        docx = require_extra("docx", "documents")
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        document = docx.Document(BytesIO(payload.data))
        for position, node in enumerate(document.element.body):
            check()
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "p":
                text = Paragraph(node, document).text
                check(len(text.encode("utf-8")))
                blocks.append(DocumentBlock(len(blocks), "paragraph", text, locator=f"body:{position}"))
            elif tag == "tbl":
                table = Table(node, document)
                rows = tuple(tuple(cell.text for cell in row.cells) for row in table.rows)
                check(sum(len(cell.encode("utf-8")) for row in rows for cell in row))
                blocks.append(DocumentBlock(len(blocks), "table", "", rows=rows, locator=f"body:{position}"))
            elif tag != "sectPr":
                qualifications.append(f"body:{position}:unrepresented_block:{tag}")
        fmt = "docx"
        qualifications.append("Ordered main-body paragraphs and table cell text; headers, footers, drawings and layout are outside this profile.")
        qualifications.append("Merged DOCX cells may repeat text across their occupied grid positions.")
        coverage = SnapshotCoverage("partial", "Ordered main-body text and table grids, with original bytes retained by identity.")
    elif payload.media_type == "text/plain":
        text = payload.data.decode(payload.charset or "utf-8", errors="strict")
        check(len(text.encode("utf-8")))
        blocks = [DocumentBlock(i, "paragraph", line, locator=f"line:{i+1}") for i, line in enumerate(text.splitlines())]
        fmt, coverage = "txt", SnapshotCoverage("complete", "All supplied text lines; original newline bytes remain in the original.")
    else:
        raise ValueError("document.format_unsupported")
    return DocumentExtract(series_id, issue_id, asset_id, payload.identity, fmt, profile_id, profile_version,
        tuple(blocks), (UsedInputReceipt.for_payload(payload, "source"),), coverage, tuple(qualifications))
