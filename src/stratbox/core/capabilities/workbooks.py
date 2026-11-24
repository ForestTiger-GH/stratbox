"""Reusable workbook decoding and readable projections without interpretation."""
from __future__ import annotations

from typing import Mapping

from stratbox.core.execution.contracts import OperationFailure
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.core.formats.spreadsheets.workbook_input import WorkbookError
from stratbox.shared.data.workbook_cells import WorkbookCells
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.scalars import encode_scalar
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import canonical_manifest_bytes


def workbook_decode(request: Mapping, invocation):
    material = request["material"]
    if not isinstance(material, SourcePayload):
        raise OperationFailure("workbook.source_payload_required")
    try:
        return read_workbook_cells(material.data, budget=invocation.budget, checkpoint=invocation.check_cancelled)
    except WorkbookError as error:
        raise OperationFailure(str(error)) from None


def workbook_readable(request: Mapping, invocation):
    workbook = request["workbook"]
    if not isinstance(workbook, WorkbookCells):
        raise OperationFailure("workbook.cells_required")
    def records():
        yield {"kind": "workbook", "sha256": workbook.identity.sha256, "size": workbook.identity.size}
        for sheet in workbook.sheets:
            invocation.check_cancelled()
            yield {"kind": "sheet", "name": sheet.name, "index": sheet.index,
                "rows": sheet.rows, "columns": sheet.columns, "merged_ranges": sheet.merged_ranges}
            for cell in sheet.cells:
                invocation.check_cancelled()
                kind, token = encode_scalar(cell.value)
                yield {"kind": "cell", "sheet": sheet.name, "coordinate": cell.coordinate,
                    "value_type": kind, "value": token, "raw_token": cell.raw_token, "source_kind": cell.kind,
                    "formula": cell.formula, "number_format": cell.number_format,
                    "formula_attributes": cell.formula_attributes, "evidence_kind": cell.evidence_kind}
    chunks, size = [], 0
    limit = request.get("max_bytes", 32 * 1024 * 1024)
    for record in records():
        chunk = canonical_manifest_bytes(record) + b"\n"
        size += len(chunk)
        if size > limit:
            raise OperationFailure("workbook.readable_size_limit")
        invocation.budget.check("output_bytes", size)
        chunks.append(chunk)
    return Representation("workbook.readable.jsonl", 1, "application/x-ndjson", b"".join(chunks), "utf-8")
