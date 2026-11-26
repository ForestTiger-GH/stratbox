"""Rosstat product content and explicit workbook layout over accepted values."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import date, timedelta

from stratbox.shared.data.selection import observation_query, select_observations
from stratbox.shared.data.values import EncodedProduct, SourceDataset, View, fingerprint
from ..common.kep2 import KEP2_INDICATORS, KEP2_MEASURES


@dataclass(frozen=True)
class MonthlyWorkbookSettings:
    sheet_name: str = "Rosstat"
    headers: tuple[str, str] = ("Indicator", "Measure")
    header_row: int = 1
    freeze_panes: str | None = None
    number_format: str = "0.00"
    date_format: str = "yyyy-mm-dd"
    date_cells: str = "iso"
    include_evidence: bool = True
    include_metadata: bool = True
    include_empty_periods: bool = False
    missing_display: str = "blank"

    def __post_init__(self):
        if (not isinstance(self.sheet_name, str) or not self.sheet_name or len(self.sheet_name) > 31
                or any(char in self.sheet_name for char in "[]:*?/\\")
                or self.sheet_name.casefold() in {"evidence", "metadata"}):
            raise ValueError("rosstat.kep2.sheet_name_invalid")
        if type(self.header_row) is not int or not 1 <= self.header_row <= 1000:
            raise ValueError("rosstat.kep2.header_row_invalid")
        if len(self.headers) != 2 or any(not isinstance(value, str) or not value for value in self.headers):
            raise ValueError("rosstat.kep2.headers_invalid")
        object.__setattr__(self, "headers", tuple(self.headers))
        if any(type(getattr(self, name)) is not bool for name in
                ("include_evidence", "include_metadata", "include_empty_periods")):
            raise ValueError("rosstat.kep2.boolean_setting_required")
        if self.missing_display not in {"blank", "source_token"}:
            raise ValueError("rosstat.kep2.missing_display_invalid")
        if self.date_cells not in {"iso", "date"}:
            raise ValueError("rosstat.kep2.date_cells_invalid")
        if any(not isinstance(value, str) or not value for value in (self.number_format, self.date_format)):
            raise ValueError("rosstat.kep2.number_format_invalid")
        if self.freeze_panes is not None:
            from re import fullmatch
            if not isinstance(self.freeze_panes, str) or fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", self.freeze_panes) is None:
                raise ValueError("rosstat.kep2.freeze_panes_invalid")


def _settings(parameters):
    supplied = parameters.get("workbook_settings")
    if supplied is None:
        supplied = {field.name: parameters[field.name] for field in fields(MonthlyWorkbookSettings)
                    if field.name in parameters}
    if isinstance(supplied, MonthlyWorkbookSettings):
        return supplied
    if not isinstance(supplied, Mapping) or set(supplied) - {field.name for field in fields(MonthlyWorkbookSettings)}:
        raise ValueError("rosstat.kep2.workbook_settings_invalid")
    return MonthlyWorkbookSettings(**supplied)


def monthly(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != "rosstat.short_term_indicators":
        raise ValueError("rosstat.kep2.dataset_required")
    allowed = {item.id for item in KEP2_INDICATORS}
    for row in dataset.rows:
        context.checkpoint()
        if row.get("frequency") != "monthly":
            continue
        if row.get("indicator_id") not in allowed or row.get("subject_namespace") != "iso3166-1" or row.get("subject") != "RU":
            raise ValueError("rosstat.kep2.product_scope_conflict")
    query = observation_query(context.parameters.get("observation_query", {}))
    if "frequency" in query.filters and query.filters["frequency"] != ("monthly",):
        raise ValueError("rosstat.kep2.monthly_query_required")
    query = replace(query, filters={**query.filters, "frequency": ("monthly",)})
    selected = select_observations(dataset, query)
    if not selected.rows:
        raise ValueError("rosstat.kep2.monthly_values_required")
    layout = _settings(context.parameters)
    return {"view": View(selected, {"view_id": "rosstat.kep2.monthly",
        "date_convention": "next_period_start", "workbook_settings": {field.name: getattr(layout, field.name)
            for field in fields(layout)}}, (*dataset.lineage, dataset.identity), source_uses=selected.source_uses)}


def render_monthly_workbook(inputs, settings, context):
    view = inputs["view"]
    if not isinstance(view, View) or view.settings.get("view_id") != "rosstat.kep2.monthly":
        raise ValueError("rosstat.kep2.monthly_view_required")
    from stratbox.core.runtime.dependencies import require_extra
    from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
    openpyxl = require_extra("openpyxl", "excel")
    from openpyxl.styles import Font, PatternFill
    dataset = view.value
    layout = _settings(view.settings)
    index, dates = {}, set()
    selected_indicators, selected_measures = set(), set()
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
        selected_indicators.add(row["indicator_id"])
        selected_measures.add(row["measure"])
        if layout.include_empty_periods or row["value"] is not None:
            dates.add(display)
    periods = tuple(sorted(dates))
    if not periods:
        raise ValueError("rosstat.kep2.product_empty")
    book = openpyxl.Workbook()
    try:
        sheet = book.active
        sheet.title = layout.sheet_name
        headings = tuple(period.isoformat() for period in periods) if layout.date_cells == "iso" else periods
        for column, value in enumerate((*layout.headers, *headings), 1):
            cell = sheet.cell(layout.header_row, column, value)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="DAE3F3")
            if column > 2:
                cell.number_format = layout.date_format
        ordinal = layout.header_row + 1
        for measure, label, _ in KEP2_MEASURES:
            if measure not in selected_measures:
                continue
            for indicator in KEP2_INDICATORS:
                if indicator.id not in selected_indicators:
                    continue
                sheet.cell(ordinal, 1, indicator.label)
                sheet.cell(ordinal, 2, label)
                for column, period in enumerate(periods, 3):
                    observed = index.get((indicator.id, measure, period), {})
                    value = observed.get("value")
                    if value is None and layout.missing_display == "source_token":
                        value = observed.get("raw_token")
                    cell = sheet.cell(ordinal, column, value)
                    cell.number_format = layout.number_format
                ordinal += 1
            ordinal += 1
        sheet.freeze_panes = layout.freeze_panes or "C" + str(layout.header_row + 1)
        sheet.auto_filter.ref = f"A{layout.header_row}:{sheet.cell(max(layout.header_row, ordinal - 2), len(periods) + 2).coordinate}"
        if layout.include_evidence:
            evidence = book.create_sheet("Evidence")
            names = ("indicator_id", "measure", "period_start", "period_end", "display_date", "value", "value_status",
                "unit", "scale", "unit_literal", "raw_token", "footnotes", "number_format", "evidence_ref")
            evidence.append(names)
            for row in dataset.rows:
                context.checkpoint()
                evidence.append(tuple(str(row.get(name)) if row.get(name) is not None else None for name in names))
            evidence.freeze_panes = "A2"
            evidence.auto_filter.ref = evidence.dimensions
        if layout.include_metadata:
            metadata = book.create_sheet("Metadata")
            metadata.append(("source_id", dataset.source_id))
            metadata.append(("dataset_identity", dataset.identity))
            metadata.append(("coverage", dataset.assessment.status))
            metadata.append(("scope", "Explicit monthly subset of reviewed source indicators; native index bases preserved."))
            metadata.append(("settings_identity", fingerprint(layout)))
        data = openpyxl_bytes(book, literal_text=True)
    finally:
        book.close()
    return {"product": EncodedProduct(data,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", view.lineage,
        {"view_id": "rosstat.kep2.monthly", "source_basis": dataset.identity,
         "settings_identity": fingerprint(layout)}, source_uses=view.source_uses, assessment=view.assessment)}
