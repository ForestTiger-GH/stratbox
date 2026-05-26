"""
output — сохранение итоговой Excel-книги по счетам эскроу через FileStore stratbox.

Поддерживаются два режима:
- обычный .xlsx;
- zip-архив, внутри которого лежит .xlsx.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from stratbox.base import ioapi as ia
from stratbox.base.filestore import FileStore



def _normalize_xlsx_path(path: str) -> str:
    """Гарантирует расширение .xlsx у итогового файла."""
    text = str(path).strip()
    if not text.lower().endswith(".xlsx"):
        return f"{text}.xlsx"
    return text



def _normalize_zip_path(path: str) -> str:
    """Гарантирует расширение .zip у итогового архива."""
    text = str(path).strip()
    if not text.lower().endswith(".zip"):
        return f"{text}.zip"
    return text



def workbook_to_bytes(workbook: Workbook) -> bytes:
    """Сериализует openpyxl Workbook в bytes без локального временного файла."""
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()



def save_workbook_xlsx(
    out_path: str,
    workbook: Workbook,
    *,
    store: FileStore | None = None,
) -> str:
    """Сохраняет книгу как .xlsx через FileStore stratbox."""
    final_path = _normalize_xlsx_path(out_path)
    ia.bytes.write_bytes(final_path, workbook_to_bytes(workbook), store=store)
    return final_path



def save_workbook_zip(
    out_path: str,
    workbook: Workbook,
    *,
    archive_member_name: str,
    store: FileStore | None = None,
) -> str:
    """Сохраняет книгу как .zip-архив с одним xlsx-файлом внутри."""
    final_path = _normalize_zip_path(out_path)
    member_name = _normalize_xlsx_path(archive_member_name)
    ia.zip.write_zip_from_memory(
        final_path,
        {member_name: workbook_to_bytes(workbook)},
        store=store,
    )
    return final_path


__all__ = [
    "save_workbook_xlsx",
    "save_workbook_zip",
    "workbook_to_bytes",
]
