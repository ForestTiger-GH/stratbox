"""Render a constructed openpyxl workbook to deterministic OOXML bytes."""

from datetime import datetime
from shutil import copyfileobj
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from stratbox.base.limits import BudgetMeter
from stratbox.base.utils.optional_deps import require_extra
from .bytes import OutputBuffer

_EPOCH = datetime(1980, 1, 1)


class _WorkbookZip(ZipFile):
    @staticmethod
    def _entry(name):
        entry = ZipInfo(name)
        entry.compress_type = ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        return entry

    def writestr(self, name, data, compress_type=None, compresslevel=None):
        entry = self._entry(name.filename if isinstance(name, ZipInfo) else name)
        super().writestr(entry, data, compress_type, compresslevel)

    def write(self, filename, arcname=None, compress_type=None, compresslevel=None):
        entry = self._entry(arcname if arcname is not None else str(filename))
        if compress_type is not None:
            entry.compress_type = compress_type
        with open(filename, "rb") as source, self.open(entry, "w") as target:
            copyfileobj(source, target)


def openpyxl_bytes(workbook, *, literal_text: bool = False, budget: BudgetMeter | None = None) -> bytes:
    writer = require_extra("openpyxl.writer.excel", "excel")
    workbook.properties.created = _EPOCH
    workbook.properties.modified = _EPOCH
    if literal_text:
        if workbook.vba_archive is not None or workbook._external_links:
            raise ValueError("Interactive output requires a newly constructed workbook")
        for sheet in workbook.worksheets:
            for cell in sheet._cells.values():
                if cell.data_type == "f":
                    cell.data_type = "s"
                if getattr(cell, "hyperlink", None) is not None:
                    cell.hyperlink = None
    buffer = OutputBuffer(budget)
    with _WorkbookZip(buffer, "w", ZIP_DEFLATED) as archive:
        writer.ExcelWriter(workbook, archive).write_data()
    return buffer.getvalue()
