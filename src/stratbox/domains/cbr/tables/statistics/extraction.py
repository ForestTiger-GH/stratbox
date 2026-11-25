"""Original admission to complete source-local cells, independent of models."""
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.domains.cbr.publications.catalog import source
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.workbook_cells import WorkbookCells, validate_sheet_cells
from .contracts import WorkbookFlake


def extract_workbook_value(original: IdentifiedOriginal, *, budget=None, workbook=None) -> WorkbookFlake:
    if not isinstance(original, IdentifiedOriginal) or original.format != "xlsx":
        raise ValueError("cbr.workbook.original_required")
    item = source(original.asset.series_id)
    if "xlsx" not in item.formats or item.extraction_profile != "cbr.workbook.flake":
        raise ValueError("cbr.workbook.series_format_mismatch")
    if workbook is None:
        workbook = read_workbook_cells(original.payload.data, budget=budget)
    elif not isinstance(workbook, WorkbookCells) or workbook.identity != original.payload.identity:
        raise ValueError('cbr.workbook.decoded_identity_mismatch')
    if (not workbook.sheets or tuple(sheet.index for sheet in workbook.sheets) != tuple(range(len(workbook.sheets)))
            or len({sheet.name for sheet in workbook.sheets}) != len(workbook.sheets)):
        raise ValueError('cbr.workbook.decoded_geometry_invalid')
    for sheet in workbook.sheets:
        validate_sheet_cells(sheet)
    receipt = UsedInputReceipt("original", workbook.identity, original.payload.media_type, "inline", item.series_id)
    lineage = original.lineage or (receipt,)
    return WorkbookFlake(item.series_id, original.asset.issue_id, workbook.identity,
                         item.table_profile, 1, workbook.sheets, lineage, asset_id=original.asset.asset_id)
