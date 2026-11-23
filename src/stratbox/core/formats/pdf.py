"""PDF text reading; extraction failures propagate instead of becoming empty text."""

from __future__ import annotations

from stratbox.core.storage.filestore.ports import FileStore
from stratbox.core.runtime.providers import default_filestore
from stratbox.core.runtime.dependencies import require_extra


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
    fs = default_filestore(store)

    pypdf = require_extra("pypdf", "pdf")

    data = fs.read_bytes(path)

    from io import BytesIO

    reader = pypdf.PdfReader(BytesIO(data))

    out: list[str] = []
    total = len(reader.pages)
    limit = total if max_pages is None else min(int(max_pages), total)

    for i in range(limit):
        page = reader.pages[i]
        txt = page.extract_text() or ""
        out.append(txt)

    return out
