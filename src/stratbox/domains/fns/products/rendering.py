"""CSV/JSON/XLSX rendering has no discovery, workbook extraction or mapping side effects."""
import csv
from io import StringIO

from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.representation import Representation, XLSX
from stratbox.shared.data.views import render_observation_view

from .views import PreparedView


def render(view, *, format="csv", budget=None):
    if type(view) is not PreparedView:
        raise ValueError("fns.render.prepared_view_required")
    if format != "xlsx":
        return render_observation_view(view.observation_view(), format=format)
    openpyxl = require_extra("openpyxl", "excel")
    styles = require_extra("openpyxl.styles", "excel")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Observations"
    csv_view = render_observation_view(view.observation_view(), format="csv")
    for row in csv.reader(StringIO(csv_view.data.decode("utf-8"), newline="")):
        sheet.append(row)
        if budget is not None:
            budget.charge("cells", len(row))
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = styles.Font(bold=True, color="FFFFFF")
        cell.fill = styles.PatternFill("solid", fgColor="17365D")
        sheet.column_dimensions[cell.column_letter].width = 23
    sheet.column_dimensions["L"].width = 60
    sheet.column_dimensions["R"].width = 65
    context = workbook.create_sheet("Context")
    for row in (("Series", view.context.series_id), ("Issue", view.context.issue_id),
        ("Asset", view.context.asset_id), ("Observation date", view.context.observation_date.isoformat()),
        ("Publication date", view.context.published_on.isoformat() if view.context.published_on else "unspecified"),
        ("Capture time", view.context.captured_at.isoformat() if view.context.captured_at else "unspecified"),
        ("Source dataset SHA256", view.source_identity.sha256), ("Coverage", view.coverage.status),
        ("Coverage description", view.coverage.description or ""),
        ("Numeric representation", "Exact values are text to preserve arbitrary-size integers and decimal precision."),
        *tuple(("Qualification", value) for value in view.qualifications)):
        context.append(row)
    context.column_dimensions["A"].width = 30
    context.column_dimensions["B"].width = 110
    context.freeze_panes = "B2"
    return Representation(view.context.series_id + ".view.xlsx", 1, XLSX,
        openpyxl_bytes(workbook, literal_text=True, budget=budget))
