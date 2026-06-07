"""output — совместимый фасад на канонический export-модуль домена escrow."""

from stratbox.macrobanks.escrow.export import save_workbook_xlsx, save_workbook_zip, workbook_to_bytes

__all__ = [
    "save_workbook_xlsx",
    "save_workbook_zip",
    "workbook_to_bytes",
]
