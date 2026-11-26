"""Historical legal-entity interpretation, independent of transport and decoding."""
from collections.abc import Mapping
from decimal import Decimal
from io import StringIO
import csv
import re

from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, TableEvidenceSet, WorkbookEvidence
from ..common.mappings import mapping
from .legal_numbers import code
from .legal_rows import HistoryError, _geography, _header_row, project_book
from .publications import parse_day
from ..common.evidence import interpreted_use


class CellSheet:
    def __init__(self, sheet):
        self.name, self.nrows, self.ncols = sheet.name, sheet.rows, sheet.columns
        self._cells = {(cell.row - 1, cell.column - 1): cell for cell in sheet.cells}

    def cell_value(self, row, column):
        cell = self._cells.get((row, column))
        return "" if cell is None or cell.value is None else cell.value

    def cell(self, row, column):
        return self._cells.get((row, column))


class CellBook:
    def __init__(self, workbook):
        self._sheets = {sheet.name: CellSheet(sheet) for sheet in workbook.sheets}

    def sheet_names(self):
        return tuple(self._sheets)

    def sheet_by_name(self, name):
        return self._sheets[name]


def _selected_member(names):
    valid = [name for name in names if name.casefold().endswith((".xls", ".xlsx"))
        and len(name) < 300 and not name.startswith(("/", "\\"))
        and ".." not in name.replace("\\", "/").split("/")]
    patterns = (r"\(1\)\.xlsx?\Z", r"_I\.xlsx?\Z", r"_I_[^/\\]+\.xlsx?\Z")
    selected = [name for name in valid if any(re.search(pattern, name, re.I) for pattern in patterns)]
    if len(selected) == 1:
        return selected[0]
    if len(selected) > 1:
        raise HistoryError("MULTIPLE_PART_I_WORKBOOKS")
    if len(valid) == 1:
        if re.search(r"_II(?:_[^/\\]+)?\.xlsx?\Z", valid[0], re.I):
            raise HistoryError("SOURCE_ONLY_PART_II_PRESENT")
        return valid[0]
    raise HistoryError("PART_I_WORKBOOK_UNRESOLVED")


def select_tables(inputs, settings, context):
    physical = inputs["physical"]
    evidence = (physical,) if isinstance(physical, WorkbookEvidence) else tuple(physical)
    if not evidence or any(not isinstance(item, WorkbookEvidence) for item in evidence):
        raise TypeError("fns.1yur.workbook_evidence_required")
    by_name = {}
    for index, item in enumerate(evidence):
        if item.material.source_id not in {None, settings.source_id}:
            raise ValueError("fns.1yur.source_mismatch")
        name = str(item.material.metadata.get("member", "main" if len(evidence) == 1 else f"member-{index}.xlsx"))
        if name in by_name:
            raise ValueError("fns.1yur.member_duplicate")
        by_name[name] = item
    member = "main" if tuple(by_name) == ("main",) else _selected_member(tuple(by_name))
    selected = by_name[member]
    issue_id = str(selected.material.metadata.get("issue_id", getattr(context, "parameters", {}).get("as_of", "")))
    assessment = Assessment("partial" if len(evidence) > 1 else "complete",
        tuple("fns.1yur.member_outside_selected_part_i:" + name for name in by_name if name != member))
    tables = TableEvidenceSet((selected.workbook,), selected.material, settings.source_id,
        issue_id, assessment, {"member": member, "inventory": tuple(by_name),
                               "decoded_members": tuple(item.workbook for item in evidence)})
    return {"tables": tables, "coverage": assessment}


def interpret(inputs, settings, context):
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.source_id or len(tables.tables) != 1:
        raise ValueError("fns.1yur.source_mismatch")
    issue = inputs.get("issue") or tables.issue_id or getattr(context, "parameters", {}).get("as_of")
    if isinstance(issue, Mapping):
        if issue.get("source_id", settings.source_id) != settings.source_id:
            raise ValueError("fns.1yur.issue_source_mismatch")
        issue = issue.get("as_of", issue.get("issue_id"))
    elif issue is not None and hasattr(issue, "issue_id"):
        if getattr(issue, "source_id", settings.source_id) != settings.source_id:
            raise ValueError("fns.1yur.issue_source_mismatch")
        issue = issue.issue_id
    day = parse_day(issue)
    if day.day != 1:
        raise ValueError("fns.1yur.reporting_date_invalid")
    book = CellBook(tables.tables[0])
    raw, facts = project_book(book, day, checkpoint=context.checkpoint)
    source_rows = tuple(csv.reader(StringIO(raw.decode("utf-8"))))
    header = source_rows[0]
    lookups = {}
    for field in header[2:]:
        indicator, kind = field.split("_", 1)
        sheet = book.sheet_by_name(kind)
        number_row = _header_row(sheet)
        columns = [column for column in range(2, sheet.ncols)
            if code(sheet.cell_value(number_row, column), 2) == indicator[1:]]
        if len(columns) != 1:
            raise HistoryError("SOURCE_INDICATOR_COLUMN_AMBIGUOUS")
        geography = {}
        for row in range(number_row + 1, sheet.nrows):
            geo = _geography(sheet, row)
            if geo is not None:
                if geo in geography:
                    raise HistoryError("SOURCE_GEOGRAPHY_DUPLICATE")
                geography[geo] = row
        lookups[field] = sheet, columns[0], geography
    material_id = tables.material.identity.sha256 if tables.material else "unretained"
    observations = []
    for values in source_rows[1:]:
        region, label = values[:2]
        perimeter = "published_territory" if region else (
            "published_national" if label.strip().casefold() == "российская федерация" else "published_district")
        for field, literal in zip(header[2:], values[2:]):
            sheet, column, geography = lookups[field]
            row = geography[(region, label)]
            cell = sheet.cell(row, column)
            if cell is None:
                raise HistoryError("SOURCE_SELECTED_CELL_MISSING")
            indicator, kind = field.split("_", 1)
            observations.append({"metric": field, "subject": region + ":" + label if region else label,
                "subject_namespace": "fns.1yur.geography", "region_code": region,
                "published_label": label, "source_indicator": indicator, "source_legal_kind": kind,
                "period": day.isoformat(), "period_kind": "as_of", "frequency": "monthly",
                "measure_kind": "count", "unit": "count", "scale": Decimal(1),
                "perimeter": perimeter, "value": int(literal), "value_status": "reported",
                "raw_token": cell.raw_token,
                "evidence_ref": f"sha256:{material_id}#member={tables.metadata.get('member','main')}&sheet={kind}&cell={cell.coordinate}"})
    findings = list(tables.assessment.findings)
    for name in ("national_territorial_differences", "overlapping_territory_codes", "excluded_incomplete_kind_sheets", "excluded_source_non_entity_sheets", "orientation_disagreements_count"):
        if facts.get(name):
            findings.append("fns.1yur." + name)
    findings.append("fns.1yur.reviewed_part_i_fields_only")
    assessment = Assessment("partial", tuple(findings),
        expected=tuple(header[2:]), observed=tuple(header[2:]))
    dataset = SourceDataset(settings.source_id, tuple(observations),
        {"grain": ("subject", "metric", "period", "perimeter"),
         "coverage": facts, "source_fields": tuple(header[2:]), "scope": "reviewed_part_i"},
        day.isoformat(), (tables.material.identity,) if tables.material else (), assessment,
        source_uses=interpreted_use(tables, settings.source_id, day.isoformat(),
            tuple((sheet.name, sheet.rows, sheet.columns) for sheet in tables.tables[0].sheets),
            (settings, tuple((field, mapping(day, field)) for field in header[2:]))))
    return {"dataset": dataset, "assessment": assessment}


def align(inputs, settings, context):
    dataset = inputs["dataset"]
    if dataset.source_id != settings.source_id:
        raise ValueError("fns.1yur.source_mismatch")
    day = parse_day(dataset.issue_id)
    rows, findings = [], list(dataset.assessment.findings)
    for row in dataset.rows:
        target, reason = mapping(day, row["metric"])
        if target is None:
            findings.append("fns.1yur." + reason + ":" + row["metric"])
            continue
        measure, kind = target[3:].split("__", 1)
        quantity = "stock" if measure in {"not_ceased", "bankruptcy_proceedings"} else "count"
        updated = {**row, "metric": measure, "source_field": row["metric"],
                   "legal_kind": kind, "measure_kind": quantity}
        if quantity == "count":
            updated["time_basis"] = "published_reporting_date_unspecified_accumulation"
            findings.append("fns.1yur.event_period_basis_unresolved")
        rows.append(updated)
    assessment = Assessment("partial", tuple(dict.fromkeys(findings)),
        dataset.assessment.expected, tuple(row["source_field"] for row in rows))
    value = IntegratedDataset(dataset.source_id, tuple(rows), dataset.semantics,
        dataset.issue_id, (*dataset.lineage, dataset.identity), assessment,
        source_uses=dataset.source_uses)
    return {"dataset": value, "assessment": assessment}
