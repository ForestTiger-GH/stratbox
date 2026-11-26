"""Bounded physical decoding, independent of source-table scientific meaning."""
from __future__ import annotations
from decimal import Decimal
from io import BytesIO, StringIO, TextIOWrapper
import csv
import json
import zipfile
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, ConvertedMaterial, DbfEvidence, DocumentBlock, DocumentEvidence, DocumentStructure, JsonEvidence, Material, TableEvidenceSet, WorkbookEvidence, fingerprint
from ._settings import _option
from ._values import _material
from ._physical import bounded_material_bytes, material_properties, open_material, physical_material


def _evidence_original(value):
    material = physical_material(value)
    return _material(value) if isinstance(material, Material) else value


def workbook_decode(inputs, settings, context):
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells_stream
    from stratbox.core.formats.spreadsheets.workbook_input import workbook_profile, workbook_profile_stream
    from stratbox.shared.data.workbook_cells import WorkbookCells
    original = inputs["material"]
    material = _evidence_original(original)
    budget = getattr(context, "budget", None)
    assessment = Assessment()
    max_cells = _option(context, settings, "max_cells", 5_000_000)
    with open_material(original, context) as stream:
        signature = stream.read(8)
        stream.seek(0)
        if signature.startswith(b"PK"):
            admission = workbook_profile_stream(stream, material.identity.size, budget=budget)
            if admission.observed_cells is not None and admission.observed_cells > max_cells:
                raise ExecutionFailure("workbook.cell_limit")
            if admission.kind in {"xlsx", "xlsm"}:
                value = read_workbook_cells_stream(stream, material.identity, budget=budget,
                    checkpoint=context.checkpoint, _profile=admission)
            else:
                from stratbox.core.formats.spreadsheets.binary_cells import _xlsb_stream
                stream.seek(0)
                value = WorkbookCells(_xlsb_stream(stream, budget, context.checkpoint), material.identity)
    if not signature.startswith(b"PK"):
        data = bounded_material_bytes(original, context,
            max_bytes=_option(context, settings, "max_materialized_bytes", 32 * 1024**2))
        admission = workbook_profile(data, budget=budget)
        from stratbox.core.formats.spreadsheets.binary_cells import _xls
        value = WorkbookCells(_xls(data, budget, context.checkpoint), material.identity)
    if admission.kind in {"xls", "xlsb"}:
        assessment = Assessment("partial", ("Binary decoded values retained; source numeric text and formula expressions are unavailable.",), qualifications=frozenset({"decoded_binary"}))
    if sum(len(sheet.cells) for sheet in value.sheets) > max_cells:
        raise ExecutionFailure("workbook.cell_limit")
    return {"physical": WorkbookEvidence(material, value, assessment)}


def json_decode(inputs, settings, context):
    original = inputs["material"]
    material, tokens = _evidence_original(original), {}
    data = bounded_material_bytes(original, context, max_bytes=min(
        _option(context, settings, "max_bytes", 128 * 1024 * 1024),
        _option(context, settings, "max_materialized_bytes", 32 * 1024 * 1024)))
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
    parsed = json.loads(data.decode(material.charset or "utf-8-sig"), parse_float=number, parse_int=number,
        parse_constant=lambda _: (_ for _ in ()).throw(ExecutionFailure("json.nonfinite")), object_pairs_hook=pairs)
    neutral = material
    return {"physical": JsonEvidence(neutral, convert(parsed), tokens=tokens)}


def csv_decode(inputs, settings, context):
    original = inputs["material"]
    material = _evidence_original(original)
    rows, limit = [], _option(context, settings, "max_rows", 1000000)
    with open_material(original, context) as stream, TextIOWrapper(stream,
            encoding=_option(context, settings, "encoding", material.charset or "utf-8-sig"),
            errors="strict", newline="") as text:
        reader = csv.reader(text, delimiter=_option(context, settings, "delimiter", ","))
        for row in reader:
            context.checkpoint()
            if len(rows) == limit:
                raise ExecutionFailure("csv.row_limit")
            if getattr(context, "budget", None):
                context.budget.charge("cells", len(row))
            rows.append(tuple(row))
    return {"physical": TableEvidenceSet((tuple(rows),), material)}


def dbf_decode(inputs, settings, context):
    from stratbox.core.formats.dbf_lossless import decode_dbf_stream
    from stratbox.shared.data.dbf import DBFPreservationPolicy
    from .tabular_export import dbf_encoding
    original = inputs["material"]
    material = _evidence_original(original)
    policy = inputs.get("policy", _option(context, settings, "policy", None))
    if policy is None:
        policy = DBFPreservationPolicy(encoding=_option(context, settings, "encoding", "cp866"),
            encoding_basis=_option(context, settings, "encoding_basis", "caller"))
    if not isinstance(policy, DBFPreservationPolicy):
        raise ValueError("dbf.preservation_policy_invalid")
    encoding, basis, _ = dbf_encoding(policy, original)
    with open_material(original, context) as stream:
        value = decode_dbf_stream(stream, material.identity, encoding=encoding, encoding_basis=basis,
            max_records=_option(context, settings, "max_records", 5_000_000),
            max_cells=_option(context, settings, "max_cells", 50_000_000),
            budget=getattr(context, "budget", None), checkpoint=context.checkpoint)
    header = value.header
    return {"physical": DbfEvidence(material, value.fields, value.records,
        decoded_identity=fingerprint((material.identity, value.fields, value.records, value.encoding, header)),
        encoding=value.encoding, header=header)}


def document_decode(inputs, settings, context):
    original = inputs["material"]
    material = _evidence_original(original)
    if material.identity.size > _option(context, settings, "max_bytes", 128 * 1024**2):
        raise ExecutionFailure("document.input_limit")
    blocks = []
    with open_material(original, context) as stream:
        signature = stream.read(8)
        stream.seek(0)
        if signature.startswith(b"PK"):
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
            from stratbox.core.formats.archives.members import open_zip_stream
            from stratbox.core.formats.xml import parse_xml
            with open_zip_stream(stream, material.identity.size) as package:
                if "word/document.xml" not in package.namelist():
                    raise ExecutionFailure("document.docx_required")
                parse_xml(package.read("word/document.xml"))
            stream.seek(0)
            doc = Document(stream)
            for index, node in enumerate(doc.element.body):
                context.checkpoint()
                tag = node.tag.rsplit("}", 1)[-1]
                if tag == "p":
                    blocks.append(DocumentBlock(len(blocks), "paragraph", Paragraph(node, doc).text, locator=f"body:{index}"))
                elif tag == "tbl":
                    rows = tuple(tuple(cell.text for cell in row.cells) for row in Table(node, doc).rows)
                    blocks.append(DocumentBlock(len(blocks), "table", rows=rows, locator=f"body:{index}"))
            fmt, findings = "docx", ("Main body paragraphs and table grids only; merged cells may repeat.",)
        elif signature.startswith(b"%PDF-"):
            from pypdf import PdfReader
            reader = PdfReader(stream, strict=True)
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
    return {"physical": DocumentEvidence(material, DocumentStructure(fmt, tuple(blocks), material.identity, assessment), assessment)}


def document_convert(inputs, settings, context):
    original = inputs["material"]
    descriptor, properties = physical_material(original), material_properties(original)
    material = Material(bounded_material_bytes(original, context,
        max_bytes=_option(context, settings, "max_materialized_bytes", 32 * 1024**2)),
        media_type=getattr(descriptor, "media_type", "application/octet-stream"),
        charset=getattr(descriptor, "charset", None), **properties)
    converter = context.provider("document_converter")
    limit = _option(context, settings, "max_bytes", 128 * 1024 * 1024)
    converted = converter.convert(material, target_format="docx", max_bytes=limit, checkpoint=context.checkpoint)
    converted = _material(converted)
    if converted.source_id not in {None, material.source_id} or len(converted.data) > limit or not converted.data.startswith(b"PK"):
        raise ExecutionFailure("document.conversion_invalid")
    from stratbox.core.formats.xml import parse_xml
    with zipfile.ZipFile(BytesIO(converted.data)) as archive:
        parse_xml(archive.read("word/document.xml"))
    converted = Material(converted.data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", material.source_id,
        metadata={"converted_from": material.identity.sha256}, lineage=(*material.lineage, material.identity),
        source_uses=material.source_uses)
    return {"material": converted, "evidence": ConvertedMaterial(converted, material.identity, str(getattr(converter, "provider_id", type(converter).__name__)))}
