"""Render only prepared views; never read originals, align or calculate."""
import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO

from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.representation import Representation
from .views import view_snapshot


def render_view(view, *, format="xlsx"):
    snapshot = view_snapshot(view)
    if format == "csv":
        out = StringIO(newline="")
        writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\n")
        table = snapshot.table("observations")
        writer.writerow(tuple(column.name for column in table.schema.columns))
        writer.writerows(table.rows)
        return Representation("cbr.statistics.view.csv", 1, "text/csv", out.getvalue().encode("utf-8-sig"), "utf-8-sig")
    if format != "xlsx":
        raise ValueError("cbr.statistics.render_format_unsupported")
    engine = require_extra("xlsxwriter", "excel")
    stream = BytesIO()
    with engine.Workbook(stream, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}) as workbook:
        # Fixed container metadata makes retained-view rendering reproducible.
        workbook.set_properties({"created": datetime(2000, 1, 1, tzinfo=timezone.utc)})
        header = workbook.add_format({"bold": True, "bg_color": "#16324F", "font_color": "#FFFFFF", "text_wrap": True})
        text = workbook.add_format({"text_wrap": False, "valign": "top"})
        for name, table in snapshot.tables:
            sheet = workbook.add_worksheet(name.title()[:31])
            sheet.freeze_panes(1, 0)
            sheet.set_row(0, 30)
            sheet.set_column(0, len(table.schema.columns) - 1, 22)
            for column, spec in enumerate(table.schema.columns):
                sheet.write_string(0, column, spec.name.replace("_", " ").title(), header)
            for index, row in enumerate(table.rows, 1):
                for column, value in enumerate(row):
                    if value is not None:
                        # Decimal lexemes in presentation tables remain exact;
                        # the integrated snapshot owns typed numeric values.
                        sheet.write_string(index, column, str(value), text)
            if table.rows:
                sheet.autofilter(0, 0, len(table.rows), len(table.schema.columns) - 1)
    return Representation("cbr.statistics.view.xlsx", 1,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", stream.getvalue())
