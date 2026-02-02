"""
pdf — чтение PDF поверх FileStore.

Задача:
- дать простой способ вытащить текст из PDF (для первичного анализа)

Принципы:
- PDF читается целиком в память (для типичных отчётов этого достаточно)
- библиотека опциональна: используется pypdf
- при отсутствии зависимости выдаётся понятная ошибка (или автопип при STRATBOX_AUTO_PIP=1)

Ограничения:
- извлечение текста из PDF по природе неточно (зависит от того, есть ли текстовый слой)
- если PDF — скан, потребуется OCR (в этом пакете не делается)
"""

from __future__ import annotations

from stratbox.base.filestore.base import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.base.utils.optional_deps import ensure_import


def read_text(
    path: str,
    *,
    filestore: FileStore | None = None,
    max_pages: int | None = None,
) -> str:
    """Читает текст из PDF и возвращает одной строкой."""
    pages = read_pages_text(path, filestore=filestore, max_pages=max_pages)
    return "\n\n".join(pages)


def read_pages_text(
    path: str,
    *,
    filestore: FileStore | None = None,
    max_pages: int | None = None,
) -> list[str]:
    """Читает PDF и возвращает список текстов по страницам."""
    fs = filestore or get_filestore()

    pypdf = ensure_import(
        "pypdf",
        pip_requirement="pypdf",
        hint="For PDF text extraction, install optional dependency: pypdf",
    )

    data = fs.read_bytes(path)
    reader = pypdf.PdfReader(_io_bytes(data))

    out: list[str] = []
    total = len(reader.pages)
    limit = total if max_pages is None else min(int(max_pages), total)

    for i in range(limit):
        page = reader.pages[i]
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        out.append(txt)

    return out


def _io_bytes(data: bytes):
    """Вспомогательный конструктор BytesIO (ленивый импорт)."""
    from io import BytesIO

    return BytesIO(data)
