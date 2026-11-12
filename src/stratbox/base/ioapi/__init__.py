"""Format primitives loaded when their format is requested."""

from importlib import import_module

__all__ = [
    "archive_bytes", "archives", "bytes", "csv", "dbf", "dbf_bytes", "docx", "excel", "excel_xls",
    "excel_xlsb", "excel_xlsm", "excel_xlsx", "html", "images", "pdf", "pptx", "rar", "txt",
    "workbook_bytes", "xml", "zip",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(name)
    return import_module(f"{__name__}.{name}")
