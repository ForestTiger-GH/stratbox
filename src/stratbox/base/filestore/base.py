"""
FileStore — универсальный интерфейс транспорта файлов и каталогов.

Принцип:
- FileStore отвечает за операции с путями/файлами/каталогами
- pandas/openpyxl и прочие форматы живут выше (в ioapi)

Почему интерфейс расширенный:
- в реальной работе нужно не только read/write файла,
  но и "посмотреть каталог", "обойти дерево", "переименовать", "удалить".

Важно:
- walk/glob/copy имеют дефолтные реализации поверх базовых методов,
  чтобы бэкенды (например, SMB) можно было реализовать минимально.
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

    # --- Дефолтные "удобные" методы ---

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
        Бэкенд может переопределить walk() для эффективности.
        """

        def _join(parent: str, name: str) -> str:
            # Нормальная склейка для POSIX-путей.
            # Важно: корректно обрабатывает корень "/" (иначе теряется ведущий слэш).
            if parent == "/":
                return f"/{name}"
            p = parent.rstrip("/")
            if not p or p == ".":
                return name
            return f"{p}/{name}"


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
                    # Если бэкенд не умеет точно определять тип — пропускает.
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

        Исправление:
        - корректно поддерживает абсолютные пути ("/...") и Windows drive ("C:/...").
        """
        import re
        from pathlib import PurePosixPath

        # Если wildcard нет — вернуть либо [pattern], либо []
        if not any(ch in pattern for ch in ("*", "?", "[")):
            return [pattern] if self.exists(pattern) else []

        pat = str(pattern).replace("\\", "/")

        # Сохраняет "абсолютный префикс", чтобы base не терял ведущий / или C:/
        prefix = ""
        body = pat

        m_drive = re.match(r"^[A-Za-z]:/", body)
        if m_drive:
            prefix = body[:3]  # например "C:/"
            body = body[3:]
        elif body.startswith("//"):
            prefix = "//"
            body = body[2:]
        elif body.startswith("/"):
            prefix = "/"
            body = body[1:]

        parts = [p for p in body.split("/") if p]

        base_parts: list[str] = []
        for seg in parts:
            if any(ch in seg for ch in ("*", "?", "[")):
                break
            base_parts.append(seg)

        if base_parts:
            base = prefix + "/".join(base_parts)
        else:
            # если паттерн типа "/**/*.xlsx", base должен быть "/" (а не ".")
            base = prefix.rstrip("/") if prefix else "."

        p_pat = PurePosixPath(pat)
        out: list[str] = []

        def _join(parent: str, name: str) -> str:
            if parent == "/":
                return f"/{name}"
            p = parent.rstrip("/")
            if p in ("", "."):
                return name
            return f"{p}/{name}"

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
