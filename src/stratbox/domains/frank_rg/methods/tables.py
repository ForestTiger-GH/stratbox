"""Explicit coordinate semantics for supplied Frank workbooks.

No filename establishes units, economic periods, or a reviewed publisher layout.
Built-in source records expose this obligation rather than fabricate cell maps.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote

from stratbox.shared.data.values import (Assessment, IntegratedDataset, SourceDataset,
    TableEvidenceSet, WorkbookEvidence, fingerprint)
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse


@dataclass(frozen=True)
class CellRule:
    sheet: str
    row: int
    column: int
    metric: str
    subject: str
    unit: str
    measure_kind: str
    period: str | tuple[str, str]
    frequency: str
    perimeter: str
    subject_namespace: str = "publisher"
    scale: Decimal = Decimal(1)
    dimensions: tuple[tuple[str, str], ...] = ()
    decimal_separator: str = "."
    missing_tokens: tuple[tuple[str, str], ...] = (("", "blank"), ("-", "dash"), ("—", "dash"))

    def __post_init__(self):
        if not all((self.sheet, self.metric, self.subject, self.subject_namespace, self.unit, self.frequency, self.perimeter)):
            raise ValueError("frg.cell_semantics_required")
        if type(self.row) is not int or type(self.column) is not int or min(self.row, self.column) < 1:
            raise ValueError("frg.cell_coordinate_invalid")
        if self.measure_kind not in {"stock", "flow", "index", "ratio", "count"}:
            raise ValueError("frg.measure_kind_required")
        if self.decimal_separator not in {".", ","} or not isinstance(self.scale, Decimal) or self.scale <= 0 or not self.scale.is_finite():
            raise ValueError("frg.numeric_settings_invalid")
        if isinstance(self.period, tuple):
            if len(self.period) != 2 or date.fromisoformat(self.period[0]) > date.fromisoformat(self.period[1]):
                raise ValueError("frg.interval_invalid")
            if self.measure_kind == "stock":
                raise ValueError("frg.stock_date_required")
        else:
            date.fromisoformat(self.period)
            if self.measure_kind == "flow":
                raise ValueError("frg.flow_interval_required")
        if (len(dict(self.missing_tokens)) != len(self.missing_tokens) or any(status not in {"blank", "dash", "missing", "not_applicable", "withheld"} for _, status in self.missing_tokens)):
            raise ValueError("frg.missing_token_settings_invalid")
        if len(dict(self.dimensions)) != len(self.dimensions):
            raise ValueError("frg.dimensions_invalid")


@dataclass(frozen=True)
class CellAnchor:
    sheet: str
    row: int
    column: int
    value: object
    formula: str | None = None


@dataclass(frozen=True)
class TableRules:
    source_id: str
    cells: tuple[CellRule, ...] = ()
    original_identity: ByteIdentity | None = None
    sheet_shapes: tuple[tuple[str, int, int], ...] = ()
    anchors: tuple[CellAnchor, ...] = ()
    reviewed_originals: tuple[ByteIdentity, ...] = ()
    review_evidence: str = ""


def _rules(settings, context):
    supplied = context.parameters.get("table_rules")
    rules = supplied if supplied is not None else settings
    if not isinstance(rules, TableRules) or rules.source_id != settings.source_id:
        raise ValueError("frg.table_rules_source_conflict")
    return rules


def _physical(value):
    if isinstance(value, TableEvidenceSet):
        if len(value.tables) != 1:
            raise ValueError("frg.one_physical_workbook_required")
        value = value.tables[0]
    if not isinstance(value, WorkbookEvidence):
        raise TypeError("frg.workbook_evidence_required")
    return value


def _check_geometry(physical, rules):
    if physical.workbook.identity != physical.material.identity:
        raise ValueError("frg.physical_material_identity_conflict")
    if physical.material.source_id not in {None, rules.source_id}:
        raise ValueError("frg.material_source_conflict")
    if rules.original_identity is not None and rules.original_identity != physical.material.identity:
        raise ValueError("frg.table_rules_material_conflict")
    if rules.sheet_shapes and tuple((s.name, s.rows, s.columns) for s in physical.workbook.sheets) != rules.sheet_shapes:
        raise ValueError("frg.table_geometry_unsupported")
    cells = {(sheet.name, cell.row, cell.column): cell for sheet in physical.workbook.sheets for cell in sheet.cells}
    for anchor in rules.anchors:
        cell = cells.get((anchor.sheet, anchor.row, anchor.column))
        if cell is None or type(cell.value) is not type(anchor.value) or cell.value != anchor.value or cell.formula != anchor.formula:
            raise ValueError("frg.table_anchor_mismatch")
    if rules.reviewed_originals and (not rules.anchors or not rules.sheet_shapes or not rules.review_evidence):
        raise ValueError("frg.reviewed_layout_evidence_required")


def extract(inputs, settings: TableRules, context):
    rules = _rules(settings, context)
    physical = _physical(inputs["physical"])
    context.checkpoint()
    _check_geometry(physical, rules)
    assessment = physical.assessment if rules.cells else Assessment("unknown", ("reviewed_semantic_table_rules_required",))
    result = TableEvidenceSet((physical,), physical.material, rules.source_id,
        str(context.parameters.get("issue_id", physical.material.metadata.get("issue_id", ""))),
        assessment, {"rules_basis": fingerprint(rules)})
    return {"tables": result, "coverage": assessment}


def _value(cell, rule):
    if cell is None or cell.value is None:
        if cell is not None and cell.formula is not None:
            raise ValueError("frg.formula_cache_required")
        return None, "blank", None
    raw = cell.raw_token if cell.raw_token is not None else str(cell.value)
    value = cell.value
    if isinstance(value, str):
        if value in dict(rule.missing_tokens):
            return None, dict(rule.missing_tokens)[value], value
        token = value.replace("\u00a0", "").replace("\u202f", "").strip()
        if rule.decimal_separator == ",":
            if "." in token:
                raise ValueError("frg.numeric_value_invalid")
            token = token.replace(",", ".")
        if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", token):
            raise ValueError("frg.numeric_value_invalid")
        try:
            value = Decimal(token)
        except InvalidOperation:
            raise ValueError("frg.numeric_value_invalid") from None
    if type(value) not in {int, Decimal} or isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("frg.numeric_value_invalid")
    return Decimal(value), "reported", raw


def interpret(inputs, settings: TableRules, context):
    rules = _rules(settings, context)
    tables = inputs["tables"]
    physical = _physical(tables)
    _check_geometry(physical, rules)
    if not rules.cells or (rules.original_identity is None and not rules.reviewed_originals):
        raise ValueError("frg.reviewed_table_rules_required")
    issue = tables.issue_id or str(context.parameters.get("issue_id", ""))
    if not issue:
        raise ValueError("frg.publication_issue_required")
    sheets = {sheet.name: sheet for sheet in physical.workbook.sheets}
    lookup = {(sheet.name, cell.row, cell.column): cell for sheet in physical.workbook.sheets for cell in sheet.cells}
    positions, keys, rows = set(), set(), []
    for rule in rules.cells:
        context.checkpoint()
        if not isinstance(rule, CellRule):
            raise TypeError("frg.cell_rule_required")
        position = rule.sheet, rule.row, rule.column
        if position in positions or rule.sheet not in sheets or rule.row > sheets[rule.sheet].rows or rule.column > sheets[rule.sheet].columns:
            raise ValueError("frg.cell_coordinate_unavailable")
        positions.add(position)
        key = rule.metric, rule.subject_namespace, rule.subject, rule.period, rule.frequency, rule.perimeter, tuple(sorted(rule.dimensions))
        if key in keys:
            raise ValueError("frg.duplicate_semantic_key")
        keys.add(key)
        value, status, raw = _value(lookup.get(position), rule)
        interval = isinstance(rule.period, tuple)
        rows.append({"metric": rule.metric, "subject": rule.subject, "subject_namespace": rule.subject_namespace,
            "period": rule.period, "period_kind": "interval" if interval else "as_of",
            "period_start": rule.period[0] if interval else rule.period, "period_end": rule.period[1] if interval else rule.period,
            "frequency": rule.frequency, "unit": rule.unit, "scale": rule.scale, "measure_kind": rule.measure_kind,
            "perimeter": rule.perimeter, "dimensions": rule.dimensions, "value": value, "value_status": status,
            "raw_token": raw, "source_id": rules.source_id, "issue_id": issue,
            "source_sheet": rule.sheet, "source_row": rule.row, "source_column": rule.column,
            "evidence_ref": f"sha256:{physical.material.identity.sha256}#sheet={quote(rule.sheet, safe='')}&row={rule.row}&column={rule.column}"})
    assessment = Assessment(qualifications=frozenset({"explicit_coordinate_semantics",
        "reviewed_layout" if rules.reviewed_originals else "caller_supplied_exact_material_rules"}))
    dataset = SourceDataset(rules.source_id, tuple(rows),
        {"rules_basis": fingerprint(rules), "review_evidence": rules.review_evidence,
         "grain": ("metric", "subject_namespace", "subject", "period", "frequency", "perimeter", "dimensions")},
        issue, (*physical.material.lineage, physical.material.identity), assessment,
        source_uses=(SourceUse(SourceCoordinate(source_id=rules.source_id,
            family_id="frank_rg.delivered_reports", source_group_id="reviewed_cells", issue_id=issue,
            asset_id=str(physical.material.metadata.get("asset_id", "main")),
            material_identity=physical.material.identity,
            layout_identity=fingerprint((rules.sheet_shapes, rules.anchors, tuple((cell.sheet, cell.row, cell.column) for cell in rules.cells))),
            semantic_identity=fingerprint(rules.cells)),
            "table_interpretation", "reviewed_layout" if rules.reviewed_originals else "caller_supplied_exact_material_rules",
            "sha256:" + physical.material.identity.sha256),))
    return {"dataset": dataset, "assessment": assessment}


def validate(inputs, settings: TableRules, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.source_id:
        raise ValueError("frg.dataset_source_conflict")
    keys = set()
    for row in dataset.rows:
        context.checkpoint()
        key = tuple((name, row.get(name)) for name in ("metric", "subject_namespace", "subject", "period", "frequency", "perimeter", "dimensions"))
        if key in keys:
            raise ValueError("frg.duplicate_semantic_key")
        keys.add(key)
    return {"dataset": dataset, "assessment": dataset.assessment}


def align(inputs, settings, context):
    dataset = inputs["dataset"]
    validate(inputs, settings, context)
    result = IntegratedDataset(dataset.source_id, dataset.rows,
        {**dataset.semantics, "alignment": "explicit_native_semantics"}, dataset.issue_id,
        dataset.lineage, dataset.assessment, source_uses=dataset.source_uses)
    return {"dataset": result, "assessment": result.assessment}
