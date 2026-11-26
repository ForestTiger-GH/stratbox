"""Bounded physical decoding, independent of source-table scientific meaning."""
from __future__ import annotations
from decimal import Decimal
from io import BytesIO, StringIO
import csv
import json
import zipfile
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, ConvertedMaterial, DbfEvidence, DocumentBlock, DocumentEvidence, DocumentStructure, JsonEvidence, Material, TableEvidenceSet, WorkbookEvidence, fingerprint
from ._settings import _option
from ._values import _material


def workbook_decode(inputs, settings, context):
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
    from stratbox.core.formats.spreadsheets.workbook_input import workbook_profile
    from stratbox.shared.data.workbook_cells import WorkbookCells
    material = _material(inputs["material"])
    budget = getattr(context, "budget", None)
    admission = workbook_profile(material.data, budget=budget)
    assessment = Assessment()
    if admission.kind in {"xlsx", "xlsm"}:
        value = read_workbook_cells(material.data, budget=budget, checkpoint=context.checkpoint, _profile=admission)
    else:
        from stratbox.core.formats.spreadsheets.binary_cells import _xls, _xlsb
        sheets = (_xls if admission.kind == "xls" else _xlsb)(material.data, budget, context.checkpoint)
        value = WorkbookCells(sheets, material.identity)
        assessment = Assessment("partial", ("Binary decoded values retained; source numeric text and formula expressions are unavailable.",), qualifications=frozenset({"decoded_binary"}))
    max_cells = _option(context, settings, "max_cells", 5_000_000)
    if sum(len(sheet.cells) for sheet in value.sheets) > max_cells:
        raise ExecutionFailure("workbook.cell_limit")
    neutral = material
    return {"physical": WorkbookEvidence(neutral, value, assessment)}


def json_decode(inputs, settings, context):
    material, tokens = _material(inputs["material"]), {}
    class Token(str):
        pass
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ExecutionFailure("json.duplicate_key")
            result[key] = value
        return result
    def number(token):
        return Token(token)
    def convert(value, path=()):
        if getattr(context, "budget", None):
            context.budget.charge("objects" if isinstance(value, (dict, list)) else "cells", 1)
        if isinstance(value, Token):
            tokens[path] = str(value)
            return Decimal(value) if any(c in value for c in ".eE") else int(value)
        if isinstance(value, dict):
            return {key: convert(item, (*path, key)) for key, item in value.items()}
        if isinstance(value, list):
            return tuple(convert(item, (*path, index)) for index, item in enumerate(value))
        return value
    if len(material.data) > _option(context, settings, "max_bytes", 128 * 1024 * 1024):
        raise ExecutionFailure("json.input_limit")
    parsed = json.loads(material.data.decode(material.charset or "utf-8-sig"), parse_float=number, parse_int=number,
        parse_constant=lambda _: (_ for _ in ()).throw(ExecutionFailure("json.nonfinite")), object_pairs_hook=pairs)
    neutral = material
    return {"physical": JsonEvidence(neutral, convert(parsed), tokens=tokens)}


def csv_decode(inputs, settings, context):
    material = _material(inputs["material"])
    reader = csv.reader(StringIO(material.data.decode(_option(context, settings, "encoding", material.charset or "utf-8-sig"))),
                        delimiter=_option(context, settings, "delimiter", ","))
    rows, limit = [], _option(context, settings, "max_rows", 1000000)
    for row in reader:
        context.checkpoint()
        if len(rows) == limit:
            raise ExecutionFailure("csv.row_limit")
        if getattr(context, "budget", None): context.budget.charge("cells", len(row))
        rows.append(tuple(row))
    return {"physical": TableEvidenceSet((tuple(rows),), material)}


def dbf_decode(inputs, settings, context):
    from stratbox.core.formats.dbf_lossless import decode_dbf
    material = _material(inputs["material"])
    encoding = _option(context, settings, "encoding", "cp866")
    value = decode_dbf(material.data, encoding=encoding, checkpoint=context.checkpoint)
    if getattr(context, "budget", None): context.budget.charge("cells", len(value.fields) * len(value.records))
    neutral = material
    return {"physical": DbfEvidence(neutral, value.fields, value.records,
        decoded_identity=fingerprint((material.identity, value.fields, value.records, encoding)), encoding=encoding)}


def document_decode(inputs, settings, context):
    material = _material(inputs["material"])
    blocks = []
    if material.data.startswith(b"PK"):
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        from stratbox.core.formats.archives.members import open_zip
        from stratbox.core.formats.xml import parse_xml
        with open_zip(material.data) as package:
            if "word/document.xml" not in package.namelist():
                raise ExecutionFailure("document.docx_required")
            parse_xml(package.read("word/document.xml"))
        doc = Document(BytesIO(material.data))
        for index, node in enumerate(doc.element.body):
            context.checkpoint()
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "p":
                blocks.append(DocumentBlock(len(blocks), "paragraph", Paragraph(node, doc).text, locator=f"body:{index}"))
            elif tag == "tbl":
                rows = tuple(tuple(cell.text for cell in row.cells) for row in Table(node, doc).rows)
                blocks.append(DocumentBlock(len(blocks), "table", rows=rows, locator=f"body:{index}"))
        fmt, findings = "docx", ("Main body paragraphs and table grids only; merged cells may repeat.",)
    elif material.data.startswith(b"%PDF-"):
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(material.data), strict=True)
        if reader.is_encrypted or len(reader.pages) > _option(context, settings, "max_pages", 10000):
            raise ExecutionFailure("document.pdf_limits")
        for index, page in enumerate(reader.pages):
            context.checkpoint()
            try:
                blocks.append(DocumentBlock(index, "page", page.extract_text() or "", index + 1, locator=f"page:{index+1}"))
            except Exception as error:
                blocks.append(DocumentBlock(index, "error", "page_text_extraction_failed:" + type(error).__name__, index + 1, locator=f"page:{index+1}"))
        fmt, findings = "pdf", ("Text extraction only; table geometry and OCR are not established.",)
    else:
        raise ExecutionFailure("document.format_unsupported")
    findings = (*findings, *(block.text for block in blocks if block.kind == "error"))
    assessment = Assessment("partial", findings)
    if getattr(context, "budget", None):
        context.budget.charge("cells", sum(sum(map(len, block.rows)) for block in blocks))
    neutral = material
    return {"physical": DocumentEvidence(neutral, DocumentStructure(fmt, tuple(blocks), material.identity, assessment), assessment)}


def document_convert(inputs, settings, context):
    material, converter = _material(inputs["material"]), context.provider("document_converter")
    limit = _option(context, settings, "max_bytes", 128 * 1024 * 1024)
    converted = converter.convert(material, target_format="docx", max_bytes=limit, checkpoint=context.checkpoint)
    converted = _material(converted)
    if converted.source_id not in {None, material.source_id} or len(converted.data) > limit or not converted.data.startswith(b"PK"):
        raise ExecutionFailure("document.conversion_invalid")
    from stratbox.core.formats.xml import parse_xml
    with zipfile.ZipFile(BytesIO(converted.data)) as archive:
        parse_xml(archive.read("word/document.xml"))
    converted = Material(converted.data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", material.source_id,
        metadata={"converted_from": material.identity.sha256}, lineage=(*material.lineage, material.identity))
    return {"material": converted, "evidence": ConvertedMaterial(converted, material.identity, str(getattr(converter, "provider_id", type(converter).__name__)))}
