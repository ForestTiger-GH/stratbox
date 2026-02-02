"""
pdf — чтение PDF поверх FileStore.

Задача:
- дать простой способ вытащить текст из PDF (для первичного анализа)

Принципы:
- библиотека опциональна: используется pypdf
- при отсутствии зависимости выдаётся понятная ошибка (или автопип при STRATBOX_AUTO_PIP=1)

Ограничения:
- извлечение текста из PDF зависит от наличия текстового слоя
- если PDF — скан, потребуется OCR (здесь не реализовано)
"""

from __future__ import annotations

from stratbox.base.filestore.base import FileStore
from stratbox.base.runtime import get_filestore
from stratbox.base.utils.optional_deps import ensure_import


def read_text(
    path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    max_pages: int | None = None,
) -> str:
    pages = read_pages_text(path, store=store, auto_install=auto_install, max_pages=max_pages)
    return "\n\n".join(pages)


def read_pages_text(
    path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    max_pages: int | None = None,
) -> list[str]:
    fs = store or get_filestore()

    pypdf = ensure_import(
        "pypdf",
        pip_requirement="pypdf",
        auto_install=auto_install,
        hint="For PDF text extraction, install optional dependency: pypdf",
    )

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
