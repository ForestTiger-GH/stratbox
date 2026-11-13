"""Build a workbook for interactive use from a literal UTF-8 CSV."""

from csv import reader
from io import StringIO

from stratbox.base.ioapi.workbook_bytes import openpyxl_bytes
from stratbox.base.limits import BudgetMeter, ExecutionBudget
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import Representation
from stratbox.data.representation import CSV, XLSX


def spreadsheet_view(
    source: Representation, *, limits: ExecutionBudget | None = None,
) -> Representation:
    """Preserve literal fields as text cells and keep the original CSV separate."""
    if source.media_type != CSV or source.encoding not in {None, "utf-8"}:
        raise ValueError("Expected a literal UTF-8 CSV representation")
    meter = BudgetMeter(ExecutionBudget.intersect(
        limits, ExecutionBudget(input_bytes=16 * 1024**2, cells=1_000_000)
    ))
    meter.charge("input_bytes", source.identity.size)
    workbook = require_extra("openpyxl", "excel").Workbook()
    sheet = workbook.active
    for index, row in enumerate(reader(StringIO(source.data.decode("utf-8"), newline=""), strict=True), 1):
        meter.checkpoint()
        meter.charge("cells", len(row))
        if index > 1_048_576 or len(row) > 16_384 or any(len(value) > 32_767 for value in row):
            raise ValueError("CSV field exceeds the spreadsheet format")
        sheet.append(row)
        for cell in sheet[index]:
            cell.data_type = "s"
    data = openpyxl_bytes(workbook, literal_text=True)
    meter.charge("output_bytes", len(data))
    return Representation("spreadsheet.literal-text", 1, XLSX, data)
