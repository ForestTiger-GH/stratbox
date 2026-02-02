"""
FileStore — универсальный интерфейс транспорта файлов.

Принцип:
- FileStore отвечает за операции с путями/файлами/каталогами (потоки/байты/каталог)
- pandas/openpyxl и прочие форматы живут выше (в ioapi)

Почему интерфейс расширенный:
- в корпоративной среде часто нужно не только read/write файла,
  но и "посмотреть каталог", "обойти дерево", "переименовать", "удалить".
- доменный код (ноутбуки/скрипты) не должен зависеть от того, локальная это ФС или SMB.

Важно:
- методы walk/glob/copy имеют дефолтные реализации поверх базовых методов,
  чтобы бэкенды могли быть проще.
"""

from __future__ import annotations

from typing import BinaryIO, Iterator, Protocol, Tuple

from stratbox.base.filestore.types import FileStat


class FileStore(Protocol):
    """Универсальный транспорт файлов и каталогов."""

    # --- Потоки ---

    def open_read(self, path: str) -> BinaryIO:
        """Открывает бинарный поток чтения."""
        ...

    def open_write(self, path: str) -> BinaryIO:
        """Открывает бинарный поток записи."""
        ...

    # --- Базовые операции ---

    def exists(self, path: str) -> bool:
        """Проверяет существование файла/каталога."""
        ...

    def is_file(self, path: str) -> bool:
        """Проверяет, что путь существует и является файлом."""
        ...

    def is_dir(self, path: str) -> bool:
        """Проверяет, что путь существует и является каталогом."""
        ...

    def stat(self, path: str) -> FileStat:
        """Возвращает метаданные файла/каталога."""
        ...

    def listdir(self, path: str) -> list[str]:
        """Возвращает список имён (без путей) внутри каталога."""
        ...

    def makedirs(self, path: str) -> None:
        """Создаёт каталог (рекурсивно)."""
        ...

    def remove(self, path: str) -> None:
        """Удаляет файл."""
        ...

    def rmdir(self, path: str) -> None:
        """Удаляет пустой каталог."""
        ...

    def rmtree(self, path: str) -> None:
        """Удаляет каталог рекурсивно (вместе с содержимым)."""
        ...

    def rename(self, src: str, dst: str) -> None:
        """Переименовывает/перемещает файл или каталог."""
        ...

    # --- Удобные дефолтные реализации ---

    def read_bytes(self, path: str) -> bytes:
        """Читает файл целиком (байтами)."""
        with self.open_read(path) as f:
            return f.read()

    def write_bytes(self, path: str, data: bytes) -> None:
        """Пишет файл целиком (байтами)."""
        with self.open_write(path) as f:
            f.write(data)

    def copy(self, src: str, dst: str) -> None:
        """Копирует файл (fallback: read_bytes + write_bytes)."""
        self.write_bytes(dst, self.read_bytes(src))

    def walk(self, top: str) -> Iterator[Tuple[str, list[str], list[str]]]:
        """Рекурсивный обход каталога (аналог os.walk).

        Возвращает:
        - dirpath: путь каталога
        - dirnames: имена подкаталогов
        - filenames: имена файлов

        Дефолтная реализация построена поверх listdir/is_dir/is_file.
        Бэкенд может переопределить для эффективности.
        """

        def _join(parent: str, name: str) -> str:
            parent = parent.rstrip("/")
            if not parent or parent == ".":
                return name
            return f"{parent}/{name}"

        stack: list[str] = [top]

        while stack:
            dirpath = stack.pop()
            names = self.listdir(dirpath)
            names = sorted([n for n in names if n not in (".", "..")])

            dirnames: list[str] = []
            filenames: list[str] = []

            for name in names:
                full = _join(dirpath, name)
                if self.is_dir(full):
                    dirnames.append(name)
                elif self.is_file(full):
                    filenames.append(name)
                else:
                    # Если бэкенд не умеет точно определять тип, пропускает.
                    pass

            yield dirpath, dirnames, filenames

            for d in reversed(dirnames):
                stack.append(_join(dirpath, d))

    def glob(self, pattern: str) -> list[str]:
        """Возвращает список путей по маске (поддерживает **).

        Дефолтная реализация:
        - выделяет базовый каталог до первого wildcard-сегмента
        - делает walk(base)
        - фильтрует пути через PurePosixPath.match

        Замечание:
        - Используются POSIX-разделители (/). Для LocalFileStore это допустимо.
        """
        from pathlib import PurePosixPath

        if not any(ch in pattern for ch in ("*", "?", "[")):
            return [pattern] if self.exists(pattern) else []

        pat = pattern.replace("\\", "/")
        parts = [p for p in pat.split("/") if p]

        base_parts: list[str] = []
        for seg in parts:
            if any(ch in seg for ch in ("*", "?", "[")):
                break
            base_parts.append(seg)

        base = "/".join(base_parts) if base_parts else "."

        out: list[str] = []
        p_pat = PurePosixPath(pat)

        def _join(parent: str, name: str) -> str:
            parent = parent.rstrip("/")
            if parent in ("", "."):
                return name
            return f"{parent}/{name}"

        for dirpath, dirnames, filenames in self.walk(base):
            for dn in dirnames:
                full = _join(dirpath, dn)
                if PurePosixPath(full).match(str(p_pat)):
                    out.append(full)
            for fn in filenames:
                full = _join(dirpath, fn)
                if PurePosixPath(full).match(str(p_pat)):
                    out.append(full)

        return sorted(set(out))
