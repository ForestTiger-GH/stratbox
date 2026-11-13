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

from dataclasses import dataclass, field
from typing import BinaryIO, ContextManager, Iterator, Literal, Protocol, Tuple

from stratbox.base.filestore.paths import child_path
from stratbox.base.filestore.types import FileStat, FileVersion
from stratbox.data.evidence import ByteIdentity


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

        stack: list[str] = [top]

        while stack:
            dirpath = stack.pop()
            names = self.listdir(dirpath)
            names = sorted([n for n in names if n not in (".", "..")])

            dirnames: list[str] = []
            filenames: list[str] = []

            for name in names:
                full = child_path(dirpath, name)
                if self.is_dir(full):
                    dirnames.append(name)
                elif self.is_file(full):
                    filenames.append(name)
                else:
                    # Если бэкенд не умеет точно определять тип — пропускает.
                    pass

            yield dirpath, dirnames, filenames

            for d in reversed(dirnames):
                stack.append(child_path(dirpath, d))

                
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
            base = prefix or "."

        p_pat = PurePosixPath(pat)
        out: list[str] = []

        for dirpath, dirnames, filenames in self.walk(base):
            for dn in dirnames:
                full = child_path(dirpath, dn)
                if PurePosixPath(full).match(str(p_pat)):
                    out.append(full)
            for fn in filenames:
                full = child_path(dirpath, fn)
                if PurePosixPath(full).match(str(p_pat)):
                    out.append(full)

        return sorted(set(out))


class SourceStore(Protocol):
    """Read one object within the provider's assigned scope."""

    def open_read(self, path: str) -> BinaryIO: ...


class FileVersionReader(Protocol):
    def stat(self, path: str) -> FileStat: ...
    def inspect_file(self, path: str) -> FileVersion: ...


WriteMode = Literal["immutable", "replace_expected_revision", "best_effort_verified"]


class StagedWrite(Protocol):
    stream: BinaryIO

    def commit(self, mode: WriteMode, expected_revision: str | None) -> bool:
        """Commit once. False is a known create or revision conflict."""
        ...


class StagedWriter(SourceStore, Protocol):
    """Private staging and commit owned by the same receiving provider."""

    def stage_write(self, destination: str) -> ContextManager[StagedWrite]: ...


@dataclass(frozen=True, slots=True)
class FileMutation:
    operation_id: str
    effect_id: str
    plan_identity: ByteIdentity
    kind: Literal["copy", "rename", "remove", "write"]
    directory: str | None = field(default=None, repr=False)
    source: FileVersion | None = field(default=None, repr=False)
    destination: str | None = field(default=None, repr=False)
    content: ByteIdentity | None = None
    mode: WriteMode | None = None
    expected_revision: str | None = field(default=None, repr=False)


class ScopedMutationStore(Protocol):
    """The store checks current scope, plan, versions and action at commit."""

    def commit_mutation(self, intent: FileMutation, data: bytes | None) -> bool: ...


class ScopedStagedWrite(StagedWrite, Protocol):
    """The receiving writer checks the exact intent and staged bytes at commit."""

    def commit_admitted(self, intent: FileMutation) -> bool: ...


class AtomicCreateStore(Protocol):
    """Commit bytes only if the destination is absent at the commit point."""

    def create_if_absent(self, path: str, data: bytes) -> bool: ...


class RevisionStore(Protocol):
    """Commit only if the authoritative revision still matches."""

    def replace_if_revision(self, path: str, data: bytes, expected_revision: str) -> bool: ...


class GuardedDirectoryStore(Protocol):
    """Conditional file effects within a caller-owned directory.

    The guard serializes writers participating in the store's contract.
    Methods must reject unsupported conditional effects before mutation.
    """

    def directory_identity(self, path: str) -> str: ...
    def guard_directory(self, path: str) -> ContextManager[None]: ...
    def inspect_file(self, path: str) -> FileVersion: ...
    def remove_expected(self, expected: FileVersion) -> bool: ...
    def rename_expected(self, expected: FileVersion, target: str) -> bool: ...
