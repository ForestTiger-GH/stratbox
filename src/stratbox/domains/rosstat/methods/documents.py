"""Exact reviewed document regions and cell semantics as ordinary action settings.

These procedures preserve explicit supplied-map functionality. They provide no
claim that the unreviewed national publication has a built-in numerical map.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from stratbox.shared.data.values import Assessment, DocumentEvidence, SourceDataset, TableEvidenceSet, fingerprint
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from .kep2 import numeric_token


@dataclass(frozen=True)
class TextRegion:
    block_ordinal: int
    table_id: str
    first_line: int
    last_line: int
    columns: int
    separator: str | None = None
    column_starts: tuple[int, ...] = ()

    def __post_init__(self):
        if self.block_ordinal < 0 or not self.table_id or self.first_line < 1 or self.last_line < self.first_line or self.columns < 1:
            raise ValueError("rosstat.document_region_invalid")
        if bool(self.separator) == bool(self.column_starts):
            raise ValueError("rosstat.document_geometry_required")
        if self.column_starts and (self.column_starts[0] != 0 or len(self.column_starts) != self.columns
                or tuple(sorted(set(self.column_starts))) != self.column_starts):
            raise ValueError("rosstat.document_columns_invalid")


@dataclass(frozen=True)
class DocumentCell:
    table_id: str
    row: int
    column: int
    metric: str
    subject: str
    subject_namespace: str
    period: str | tuple[str, str]
    frequency: str
    unit: str
    measure_kind: str
    perimeter: str
    scale: Decimal = Decimal(1)
    dimensions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not all((self.table_id, self.metric, self.subject, self.subject_namespace,
                self.frequency, self.unit, self.perimeter)) or min(self.row, self.column) < 1:
            raise ValueError("rosstat.document_cell_semantics_required")
        if self.measure_kind not in {"stock", "flow", "count", "ratio", "index"}:
            raise ValueError("rosstat.document_measure_required")
        if not isinstance(self.scale, Decimal) or not self.scale.is_finite() or self.scale <= 0:
            raise ValueError("rosstat.document_scale_invalid")
        if isinstance(self.period, tuple):
            if len(self.period) != 2 or date.fromisoformat(self.period[0]) > date.fromisoformat(self.period[1]):
                raise ValueError("rosstat.document_interval_invalid")
            if self.measure_kind == "stock":
                raise ValueError("rosstat.document_period_semantics_conflict")
        else:
            date.fromisoformat(self.period)
            if self.measure_kind == "flow":
                raise ValueError("rosstat.document_period_semantics_conflict")
        if len(dict(self.dimensions)) != len(self.dimensions):
            raise ValueError("rosstat.document_dimensions_invalid")


@dataclass(frozen=True)
class DocumentRules:
    source_id: str
    material_identity: ByteIdentity
    review_evidence: str
    regions: tuple[TextRegion, ...]
    cells: tuple[DocumentCell, ...]


@dataclass(frozen=True)
class DocumentTable:
    id: str
    rows: tuple[tuple[str, ...], ...]
    page: int | None
    source_block: int


def extract(inputs, settings: DocumentRules, context):
    physical = inputs["physical"]
    if not isinstance(physical, DocumentEvidence) or not isinstance(settings, DocumentRules):
        raise TypeError("rosstat.document_rules_required")
    if physical.material.identity != settings.material_identity or not settings.review_evidence or not settings.regions:
        raise ValueError("rosstat.document_review_evidence_required")
    if getattr(physical.document, "source_identity", None) != physical.material.identity:
        raise ValueError("rosstat.document_physical_identity_conflict")
    if physical.material.source_id not in {None, settings.source_id}:
        raise ValueError("rosstat.document_source_conflict")
    blocks = physical.document.blocks
    tables = []
    if len({region.table_id for region in settings.regions}) != len(settings.regions):
        raise ValueError("rosstat.document_table_duplicate")
    for region in settings.regions:
        context.checkpoint()
        if region.block_ordinal >= len(blocks):
            raise ValueError("rosstat.document_block_missing")
        block = blocks[region.block_ordinal]
        if block.kind not in {"page", "paragraph"}:
            raise ValueError("rosstat.document_text_required")
        lines = block.text.splitlines()
        if region.last_line > len(lines):
            raise ValueError("rosstat.document_region_outside_source")
        rows = []
        for line in lines[region.first_line - 1:region.last_line]:
            if region.separator is not None:
                row = tuple(line.split(region.separator))
            else:
                if any(start > len(line) for start in region.column_starts):
                    raise ValueError("rosstat.document_short_line")
                ends = (*region.column_starts[1:], len(line))
                row = tuple(line[start:end] for start, end in zip(region.column_starts, ends))
            if len(row) != region.columns:
                raise ValueError("rosstat.document_width_mismatch")
            rows.append(row)
        tables.append(DocumentTable(region.table_id, tuple(rows), block.page, region.block_ordinal))
    assessment = Assessment("partial", qualifications=frozenset({"explicit_reviewed_text_regions", "source_document_retained"}))
    result = TableEvidenceSet(tuple(tables), physical.material, settings.source_id,
        str(context.parameters.get("issue_id", physical.material.metadata.get("issue_id", ""))), assessment,
        {"rules_basis": fingerprint(settings), "review_evidence": settings.review_evidence})
    return {"tables": result, "coverage": assessment}


def interpret(inputs, settings: DocumentRules, context):
    physical = inputs["tables"]
    if not isinstance(physical, TableEvidenceSet) or physical.material is None or physical.material.identity != settings.material_identity:
        raise ValueError("rosstat.document_material_conflict")
    if physical.source_id != settings.source_id or not settings.review_evidence or not settings.cells:
        raise ValueError("rosstat.document_semantics_required")
    if not physical.issue_id:
        raise ValueError("rosstat.document_issue_required")
    tables = {table.id: table for table in physical.tables if isinstance(table, DocumentTable)}
    rows, keys, findings = [], set(), []
    for cell in settings.cells:
        context.checkpoint()
        if not all((cell.metric, cell.subject, cell.subject_namespace, cell.unit, cell.frequency, cell.perimeter)):
            raise ValueError("rosstat.document_cell_semantics_required")
        if cell.table_id not in tables or min(cell.row, cell.column) < 1:
            raise ValueError("rosstat.document_cell_missing")
        table = tables[cell.table_id]
        if cell.row > len(table.rows) or cell.column > len(table.rows[cell.row - 1]):
            raise ValueError("rosstat.document_cell_outside_source")
        interval = isinstance(cell.period, tuple)
        if cell.measure_kind == "stock" and interval or cell.measure_kind == "flow" and not interval:
            raise ValueError("rosstat.document_period_semantics_conflict")
        key = cell.metric, cell.subject_namespace, cell.subject, cell.period, cell.perimeter, cell.dimensions
        if key in keys:
            raise ValueError("rosstat.document_duplicate_semantics")
        keys.add(key)
        raw = table.rows[cell.row - 1][cell.column - 1]
        value, status, notes = numeric_token(raw)
        if status == "unparsed":
            findings.append("unparsed:" + cell.table_id + ":" + str(cell.row) + ":" + str(cell.column))
        rows.append({"metric": cell.metric, "subject": cell.subject, "subject_namespace": cell.subject_namespace,
            "period": cell.period, "period_kind": "interval" if interval else "as_of", "frequency": cell.frequency,
            "unit": cell.unit, "scale": cell.scale, "measure_kind": cell.measure_kind, "perimeter": cell.perimeter,
            "dimensions": cell.dimensions, "value": value, "value_status": status, "raw_token": raw, "footnotes": notes,
            "evidence_ref": physical.material.identity.sha256 + "#" + cell.table_id + ":" + str(cell.row) + ":" + str(cell.column)})
    assessment = Assessment("partial" if findings else "complete", tuple(findings),
        qualifications=frozenset({"explicit_supplied_document_semantics", "selected_cells_only"}))
    result = SourceDataset(settings.source_id, tuple(rows), {"rules_basis": fingerprint(settings),
        "review_evidence": settings.review_evidence}, physical.issue_id, (*physical.material.lineage, physical.material.identity), assessment,
        source_uses=(SourceUse(SourceCoordinate(source_id=settings.source_id,
            family_id=settings.source_id, source_group_id="reviewed_document_cells", issue_id=physical.issue_id,
            asset_id=str(physical.material.metadata.get("asset_id", "main")), material_identity=physical.material.identity,
            layout_identity=fingerprint(settings.regions), semantic_identity=fingerprint(settings.cells)),
            "table_interpretation", "caller_reviewed_exact_original", "sha256:" + physical.material.identity.sha256),))
    return {"dataset": result, "assessment": assessment}
