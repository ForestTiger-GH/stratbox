"""
ioapi — единый API чтения/записи форматов поверх FileStore.

Рекомендованный импорт:
    from stratbox.base import ioapi as ia
"""

from stratbox.base.ioapi import archives, bytes, csv, excel, xml, text, dbf, docx, pptx, images

__all__ = ["bytes", "excel", "csv", "xml", "archives", "text", "dbf", "docx", "pptx", "images"]
