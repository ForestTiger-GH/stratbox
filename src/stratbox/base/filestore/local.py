"""
LocalFileStore — реализация FileStore для локальной файловой системы.

Используется вне контура, когда stratbox-plugin не установлен.

Требования:
- реализовать полный контракт FileStore
- работать как на Windows, так и на Linux/macOS

Замечание:
- LocalFileStore принимает POSIX-разделители ('/') в путях — pathlib это допускает.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, Iterator, Tuple

from stratbox.base.filestore.base import FileStore
from stratbox.base.filestore.types import FileStat


class LocalFileStore(FileStore):
    """Локальная реализация FileStore."""

    def __init__(self, root: str | None = None):
        # root используется как базовый каталог для относительных путей
        self._root = Path(root).expanduser().resolve() if root else None

    def _abs(self, path: str) -> Path:
        # Нормализация: обратные слэши приводятся к '/', pathlib на Windows это понимает.
        p = Path(str(path).replace("\\", "/"))
        if self._root and not p.is_absolute():
            p = self._root / p
        return p

    # --- Потоки ---

    def open_read(self, path: str) -> BinaryIO:
        return self._abs(path).open("rb")

    def open_write(self, path: str) -> BinaryIO:
        p = self._abs(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.open("wb")

    # --- Базовые операции ---

    def exists(self, path: str) -> bool:
        return self._abs(path).exists()

    def is_file(self, path: str) -> bool:
        return self._abs(path).is_file()

    def is_dir(self, path: str) -> bool:
        return self._abs(path).is_dir()

    def stat(self, path: str) -> FileStat:
        p = self._abs(path)
        st = p.stat()
        return FileStat(
            path=str(path),
            is_file=p.is_file(),
            is_dir=p.is_dir(),
            size=int(st.st_size),
            mtime=float(st.st_mtime),
            atime=float(st.st_atime),
            ctime=float(st.st_ctime),
        )

    def listdir(self, path: str) -> list[str]:
        p = self._abs(path)
        if not p.exists() or not p.is_dir():
            return []
        return sorted([x.name for x in p.iterdir()])

    def makedirs(self, path: str) -> None:
        self._abs(path).mkdir(parents=True, exist_ok=True)

    def remove(self, path: str) -> None:
        self._abs(path).unlink()

    def rmdir(self, path: str) -> None:
        self._abs(path).rmdir()

    def rmtree(self, path: str) -> None:
        shutil.rmtree(self._abs(path))

    def rename(self, src: str, dst: str) -> None:
        src_p = self._abs(src)
        dst_p = self._abs(dst)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        src_p.rename(dst_p)

    # --- Оптимизированные реализации ---

    def walk(self, top: str) -> Iterator[Tuple[str, list[str], list[str]]]:
        """Оптимизированный обход: использует os.walk."""
        top_p = self._abs(top)
        if not top_p.exists() or not top_p.is_dir():
            return

        for dirpath, dirnames, filenames in _os_walk(top_p):
            dp = Path(dirpath)

            # Возвращаем пути в пространстве пользователя: если root задан — делаем относительными.
            if self._root:
                try:
                    dp_rel = dp.relative_to(self._root)
                    dirpath_out = dp_rel.as_posix()
                except Exception:
                    dirpath_out = dp.as_posix()
            else:
                dirpath_out = dp.as_posix()

            yield dirpath_out, sorted(list(dirnames)), sorted(list(filenames))


def _os_walk(top: Path):
    """Вспомогательная обёртка, чтобы не тянуть os в основной класс."""
    import os

    return os.walk(top)
