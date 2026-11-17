"""Format-specific readers, writers and document codecs."""

from importlib import import_module

__all__ = ("archives", "spreadsheets", "csv", "dbf", "dbf_bytes", "docx", "html", "images", "pdf", "pptx", "txt", "xml")


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(name)
    return import_module(f"{__name__}.{name}")
