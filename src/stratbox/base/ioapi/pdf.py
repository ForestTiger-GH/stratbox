"""
pdf — чтение PDF поверх FileStore.

Задача:
- дать простой способ вытащить текст из PDF (для первичного анализа)

Принципы:
- библиотека опциональна: используется pypdf

Ограничения:
- извлечение текста из PDF зависит от наличия текстового слоя
- если PDF — скан, потребуется OCR (здесь не реализовано)
"""

from __future__ import annotations

from stratbox.base.filestore.base import FileStore
from stratbox.base.filestore import LocalFileStore
from stratbox.base.utils.optional_deps import require_extra


def read_text(
    path: str,
    store: FileStore | None = None,
    *,
    max_pages: int | None = None,
) -> str:
    pages = read_pages_text(path, store=store, max_pages=max_pages)
    return "\n\n".join(pages)


def read_pages_text(
    path: str,
    store: FileStore | None = None,
    *,
    max_pages: int | None = None,
) -> list[str]:
    fs = store if store is not None else LocalFileStore()

    pypdf = require_extra("pypdf", "pdf")

    data = fs.read_bytes(path)

    from io import BytesIO

    reader = pypdf.PdfReader(BytesIO(data))

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
