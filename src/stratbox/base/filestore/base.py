"""
FileStore — универсальный интерфейс транспорта файлов.

Принцип:
- FileStore отвечает только за "достать/положить файл" (потоки/байты)
- pandas/openpyxl и прочие форматы живут выше (в ioapi)
"""

from __future__ import annotations

from typing import BinaryIO, Protocol


class FileStore(Protocol):
    """Универсальный транспорт файлов."""

    def open_read(self, path: str) -> BinaryIO:
        """Открывает бинарный поток чтения."""
        ...

    def open_write(self, path: str) -> BinaryIO:
        """Открывает бинарный поток записи."""
        ...

    def exists(self, path: str) -> bool:
        """Проверяет существование файла/пути."""
        ...

    def listdir(self, path: str) -> list[str]:
        """Возвращает список имён в каталоге."""
        ...

    def makedirs(self, path: str) -> None:
        """Создаёт каталог (рекурсивно)."""
        ...

    def read_bytes(self, path: str) -> bytes:
        """Читает файл целиком (байтами)."""
        with self.open_read(path) as f:
            return f.read()

    def write_bytes(self, path: str, data: bytes) -> None:
        """Пишет файл целиком (байтами)."""
        with self.open_write(path) as f:
            f.write(data)