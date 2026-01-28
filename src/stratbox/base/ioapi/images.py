"""
images — чтение/запись картинок (png/jpg/jpeg/...) поверх FileStore.

Варианты использования:
- read_bytes()/write_bytes() уже достаточно для хранения.
- Здесь добавлены удобные функции через Pillow (PIL) для случаев,
  когда нужно быстро открыть изображение или сохранить его обратно.

Требует: pip install pillow
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def read_pil(path: str, store: FileStore | None = None):
    """Читает изображение и возвращает объект PIL.Image.Image."""
    try:
        from PIL import Image  # type: ignore
    except Exception as e:
        raise ImportError(
            "Image support requires optional dependency 'pillow'. "
            "Install: pip install pillow"
        ) from e

    data = read_bytes(path, store=store)
    bio = BytesIO(data)
    return Image.open(bio)


def write_pil(path: str, image, format: str | None = None, store: FileStore | None = None, **kwargs: Any) -> None:
    """
    Пишет PIL.Image.Image в файл.

    format:
    - если None, Pillow попытается определить по расширению, но это не всегда надёжно.
    """
    try:
        from PIL import Image  # type: ignore
    except Exception as e:
        raise ImportError(
            "Image support requires optional dependency 'pillow'. "
            "Install: pip install pillow"
        ) from e

    out = BytesIO()
    image.save(out, format=format, **kwargs)
    write_bytes(path, out.getvalue(), store=store)
