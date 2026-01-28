"""
text — чтение/запись txt (и любых текстовых файлов) поверх FileStore.

Эти функции полезны, когда нужно быстро читать/писать небольшие текстовые файлы:
- конфиги
- логи
- выгрузки .txt

Примечание:
- кодировка по умолчанию utf-8. Если в контуре часто встречается cp1251/cp866 — её можно передать явно.
"""

from __future__ import annotations

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def read_text(path: str, encoding: str = "utf-8", store: FileStore | None = None) -> str:
    """Читает текстовый файл целиком и возвращает строку."""
    data = read_bytes(path, store=store)
    return data.decode(encoding, errors="replace")


def write_text(path: str, text: str, encoding: str = "utf-8", store: FileStore | None = None) -> None:
    """Пишет строку в файл (полностью)."""
    data = str(text).encode(encoding, errors="replace")
    write_bytes(path, data, store=store)
