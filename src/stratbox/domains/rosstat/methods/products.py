"""Rosstat product content and workbook layout over accepted observations."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from stratbox.shared.data.values import EncodedProduct, SourceDataset, View
from ..common.kep2 import KEP2_INDICATORS, KEP2_MEASURES


def monthly(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != "rosstat.short_term_indicators":
        raise ValueError("rosstat.kep2.dataset_required")
    allowed = {item.id for item in KEP2_INDICATORS}
    rows = []
    for row in dataset.rows:
        context.checkpoint()
        if row.get("frequency") != "monthly":
            continue
        if row.get("indicator_id") not in allowed or row.get("subject_namespace") != "iso3166-1" or row.get("subject") != "RU":
            raise ValueError("rosstat.kep2.product_scope_conflict")
        rows.append(row)
    if not rows:
        raise ValueError("rosstat.kep2.monthly_values_required")
    selected = replace(dataset, rows=tuple(rows))
    return {"view": View(selected, {"view_id": "rosstat.kep2.monthly", "date_convention": "next_period_start"}, dataset.lineage)}


def render_monthly_workbook(inputs, settings, context):
    view = inputs["view"]
    if not isinstance(view, View) or view.settings.get("view_id") != "rosstat.kep2.monthly":
        raise ValueError("rosstat.kep2.monthly_view_required")
    from stratbox.core.runtime.dependencies import require_extra
    from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
    openpyxl = require_extra("openpyxl", "excel")
    from openpyxl.styles import Font, PatternFill
    dataset = view.value
    index, dates = {}, set()
    for row in dataset.rows:
        context.checkpoint()
        display = row["display_date"]
        end = row["period_end"]
        display = date.fromisoformat(display) if isinstance(display, str) else display
        end = date.fromisoformat(end) if isinstance(end, str) else end
        if row["frequency"] != "monthly" or display != end + timedelta(days=1):
            raise ValueError("rosstat.kep2.display_date_invalid")
        key = row["indicator_id"], row["measure"], display
        if key in index:
            raise ValueError("rosstat.kep2.product_duplicate_cell")
        index[key] = row
        if row["value"] is not None:
            dates.add(display)
    periods = tuple(sorted(dates))
    if not periods:
        raise ValueError("rosstat.kep2.product_empty")
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Rosstat"
    sheet.append(("Indicator", "Measure", *(period.isoformat() for period in periods)))
    for measure, label, _ in KEP2_MEASURES:
        for indicator in KEP2_INDICATORS:
            sheet.append((indicator.label, label, *(index.get((indicator.id, measure, period), {}).get("value") for period in periods)))
        sheet.append(())
    sheet.freeze_panes = "C2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DAE3F3")
    evidence = book.create_sheet("Evidence")
    names = ("indicator_id", "measure", "period_start", "period_end", "display_date", "value", "value_status",
        "unit", "scale", "unit_literal", "raw_token", "footnotes", "number_format", "evidence_ref")
    evidence.append(names)
    for row in dataset.rows:
        evidence.append(tuple(str(row.get(name)) if row.get(name) is not None else None for name in names))
    evidence.freeze_panes = "A2"
    evidence.auto_filter.ref = evidence.dimensions
    metadata = book.create_sheet("Metadata")
    metadata.append(("source_id", dataset.source_id))
    metadata.append(("dataset_identity", dataset.identity))
    metadata.append(("coverage", dataset.assessment.status))
    metadata.append(("scope", "Reviewed eleven-indicator selection; source indices remain unchanged."))
    return {"product": EncodedProduct(openpyxl_bytes(book, literal_text=True),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", dataset.lineage,
        {"view_id": "rosstat.kep2.monthly", "source_basis": dataset.identity})}
