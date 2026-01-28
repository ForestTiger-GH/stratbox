"""
ioapi — единый API чтения/записи форматов поверх FileStore.

Рекомендованный импорт:
    from stratbox.base import ioapi as ia
"""

from stratbox.base.ioapi import (
    archives,
    bytes,
    csv,
    excel,
    excel_xls,
    excel_xlsb,
    excel_xlsm,
    excel_xlsx,
    xml,
    txt,
    dbf,
    docx,
    pptx,
    images,
    zip,
    rar,
)

__all__ = [
    "bytes",
    "excel",
    "excel_xlsx",
    "excel_xlsm",
    "excel_xls",
    "excel_xlsb",
    "csv",
    "xml",
    "archives",
    "zip",
    "rar",
    "txt",
    "dbf",
    "docx",
    "pptx",
    "images",
]