"""Fiscal table interpretation over physical cells with explicit row semantics."""
from calendar import monthrange
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
import re

from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, TableEvidenceSet, WorkbookEvidence
from ..common.periods import normalize_period
from ..common.numbers import numeric_value
from ..common.evidence import interpreted_use
from ..common.evidence import issue_id
from dataclasses import replace


def _scalar(cell):
    return cell.value if cell is not None else None


def _text(cell):
    value = _scalar(cell)
    return " ".join(str(value if value is not None else "").split())


def _columns(sheet, settings):
    cells = {(cell.row, cell.column): cell for cell in sheet.cells}
    options = []
    for row in range(1, min(settings.max_header_rows, sheet.rows) + 1):
        columns = []
        for column in range(settings.first_period_column, sheet.columns + 1):
            raw = _text(cells.get((row, column)))
            if not raw:
                continue
            try:
                period = normalize_period(raw, settings.frequency)
            except ValueError:
                continue
            columns.append((column, raw, period))
        if len(columns) >= settings.minimum_periods:
            options.append((row, tuple(columns)))
    if not options:
        return None
    header_row, columns = max(options, key=lambda item: (len(item[1]), -item[0]))
    periods = tuple(column[2] for column in columns)
    if len(set(periods)) != len(periods) or tuple(sorted(periods)) != periods:
        raise ValueError("minfin.table.periods_ambiguous")
    return header_row, columns


def extract(inputs, settings, context):
    physical = inputs["physical"]
    if not isinstance(physical, WorkbookEvidence):
        raise TypeError("minfin.table.workbook_evidence_required")
    if physical.material.source_id not in {None, settings.source_id}:
        raise ValueError("minfin.table.source_mismatch")
    candidates = []
    for sheet in physical.workbook.sheets:
        context.checkpoint()
        if sheet.rows > settings.max_rows or sheet.columns > 20_000:
            raise ValueError("minfin.table.geometry_unsupported")
        selected = _columns(sheet, settings)
        if selected is not None:
            candidates.append((sheet, selected))
    choice = getattr(context, "parameters", {}).get("sheet")
    if choice is not None:
        candidates = [item for item in candidates if item[0].name == choice]
    if len(candidates) != 1:
        raise ValueError("minfin.table.single_reviewed_sheet_required")
    sheet, (header_row, columns) = candidates[0]
    metadata = {**physical.material.metadata, "header_row": header_row,
                "columns": columns, "selected_sheet": sheet.name,
                "sheet_inventory": tuple(item.name for item in physical.workbook.sheets)}
    tables = TableEvidenceSet((sheet,), physical.material, settings.source_id,
        str(metadata.get("issue_id", "")), physical.assessment, metadata)
    return {"tables": tables, "coverage": physical.assessment}


def period_details(period_id, frequency, basis, original_header=""):
    year = int(period_id[:4])
    if frequency == "annual":
        month, first = 12, 1
    elif frequency == "quarterly":
        month = int(period_id[-1]) * 3
        first = month - 2
    else:
        month = int(period_id[-2:])
        first = month
    end = date(year, month, monthrange(year, month)[1])
    if basis == "stock":
        raw = re.sub(r"\s*\*+\s*$", "", original_header).strip()
        for pattern in ("%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                end = datetime.strptime(raw, pattern).date()
                break
            except ValueError:
                pass
        return {"period": end.isoformat(), "period_kind": "as_of", "measure_kind": "stock"}
    if basis not in {"ytd", "annual", "period_flow"}:
        raise ValueError("minfin.table.period_basis_invalid")
    if basis == "annual" and frequency != "annual":
        raise ValueError("minfin.table.period_basis_mismatch")
    start = date(year, 1 if basis in {"ytd", "annual"} else first, 1)
    return {"period": (start.isoformat(), end.isoformat()), "period_kind": "interval",
            "period_start": start.isoformat(), "period_end": end.isoformat(), "measure_kind": "flow"}


def interpret(inputs, settings, context):
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.source_id or len(tables.tables) != 1:
        raise ValueError("minfin.table.source_mismatch")
    tables = replace(tables, issue_id=issue_id(inputs, tables, context, settings.source_id))
    sheet = tables.tables[0]
    cells = {(cell.row, cell.column): cell for cell in sheet.cells}
    source_rows = {}
    for row in range(int(tables.metadata["header_row"]) + 1, sheet.rows + 1):
        context.checkpoint()
        code = _text(cells.get((row, settings.code_column))).rstrip(".")
        label = _text(cells.get((row, settings.label_column)))
        if not code or not label or not re.fullmatch(r"\d+(?:\.\d+)*", code):
            continue
        if code in source_rows:
            raise ValueError("minfin.table.duplicate_source_code")
        source_rows[code] = (row, label)
    observations, findings = [], []
    digest = tables.material.identity.sha256 if tables.material else "unretained"
    rules = tuple(getattr(context, "parameters", {}).get("row_rules", settings.rows))
    if not rules:
        raise ValueError("minfin.table.row_semantics_required")
    selected_codes = {rule.code.rstrip(".") for rule in rules}
    if len(selected_codes) != len(rules):
        raise ValueError("minfin.table.duplicate_row_rules")
    for rule in rules:
        found = source_rows.get(rule.code.rstrip("."))
        if found is None or not found[1].casefold().startswith(rule.label.casefold()):
            raise ValueError("minfin.table.reviewed_layout_mismatch:" + rule.code)
        row, label = found
        basis = settings.basis if rule.basis == "source" else rule.basis
        for column, header, period_id in tables.metadata["columns"]:
            cell = cells.get((row, column))
            value = _scalar(cell)
            raw = cell.raw_token if cell is not None and cell.raw_token is not None and type(value) in {int, Decimal} else (
                str(value) if value is not None else None)
            number, status = numeric_value(raw)
            if cell is not None and cell.formula is not None and value is None:
                status = "unparsed"
                findings.append("minfin.table.formula_without_cache")
            observations.append({"metric": rule.metric, "source_code": rule.code,
                "source_label": label, "subject": "RU", "subject_namespace": "geography",
                **period_details(period_id, settings.frequency, basis, header),
                "frequency": settings.frequency, "value_basis": basis, "unit": rule.unit,
                "scale": rule.scale, "perimeter": settings.perimeter, "value": number,
                "value_status": status, "raw_token": raw,
                "evidence_ref": f"sha256:{digest}#sheet={sheet.name}&row={row}&column={column}&issue={tables.issue_id}",
                "source_header": header})
    omitted = sorted(set(source_rows) - selected_codes)
    findings.extend("minfin.table.outside_reviewed_rows:" + code for code in omitted)
    assessment = Assessment("partial" if findings else "complete", tuple(dict.fromkeys(findings)),
        expected=tuple(rule.code for rule in rules), observed=tuple(rule.code for rule in rules))
    dataset = SourceDataset(settings.source_id, tuple(observations),
        {"grain": ("metric", "subject", "period", "perimeter"), "frequency": settings.frequency,
         "source_basis": settings.basis, "scope": settings.scope, "omitted_source_codes": tuple(omitted),
         "row_semantics": {rule.metric: {"unit": rule.unit, "scale": rule.scale,
             "basis": settings.basis if rule.basis == "source" else rule.basis} for rule in rules}},
        tables.issue_id, (tables.material.identity,) if tables.material else (), assessment,
        source_uses=interpreted_use(tables, settings.source_id, settings.family_id,
            (sheet.name, sheet.rows, sheet.columns, tables.metadata["header_row"], tables.metadata["columns"]),
            (settings, rules)))
    return {"dataset": dataset, "assessment": assessment}


def validate(inputs, settings, context):
    dataset = inputs["dataset"]
    if dataset.source_id != settings.source_id:
        raise ValueError("minfin.dataset.source_mismatch")
    seen, totals = set(), {}
    for row in dataset.rows:
        key = (row["metric"], row["subject"], row["period"], row["perimeter"])
        if key in seen:
            raise ValueError("minfin.dataset.duplicate_semantic_grain")
        seen.add(key)
        semantics = dataset.semantics.get("row_semantics", {}).get(row["metric"])
        if semantics is None or row["unit"] != semantics["unit"] or row["scale"] != semantics["scale"] or row["value_basis"] != semantics["basis"]:
            raise ValueError("minfin.dataset.reviewed_unit_mismatch")
        if row["measure_kind"] == "stock" and row["period_kind"] != "as_of" or row["measure_kind"] == "flow" and row["period_kind"] != "interval":
            raise ValueError("minfin.dataset.period_basis_mismatch")
        totals.setdefault(row["period"], {})[row["metric"]] = row
    for period, metrics in totals.items():
        if all(name in metrics and metrics[name]["value_status"] == "reported" for name in ("budget.revenue", "budget.expenditure", "budget.balance")):
            if abs(metrics["budget.balance"]["value"] - (metrics["budget.revenue"]["value"] - metrics["budget.expenditure"]["value"])) > Decimal("0.05"):
                raise ValueError("minfin.dataset.budget_balance_inconsistent")
        if all(name in metrics and metrics[name]["value_status"] == "reported" for name in ("nwf.total", "nwf.other_assets")):
            total, other = (metrics[name]["value"] for name in ("nwf.total", "nwf.other_assets"))
            if total < 0 or other < 0 or other > total:
                raise ValueError("minfin.dataset.fund_balance_invalid")
    return {"dataset": dataset, "assessment": dataset.assessment}


def align(inputs, settings, context):
    result = validate(inputs, settings, context)
    dataset = result["dataset"]
    value = IntegratedDataset(dataset.source_id, dataset.rows, dataset.semantics, dataset.issue_id,
        (*dataset.lineage, dataset.identity), dataset.assessment, source_uses=dataset.source_uses)
    return {"dataset": value, "assessment": value.assessment}
