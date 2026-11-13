"""Local file and directory commands."""

from __future__ import annotations

from contextlib import contextmanager
from errno import ENOTSUP, EXDEV
from hashlib import sha256
import os
import stat
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, Callable, Iterator, Tuple

from stratbox.base.filestore.base import FileStore, WriteMode
from stratbox.base.filestore.types import (
    DIRECTORY_GUARD_NAME,
    FileStat,
    FileVersion,
    MutationRejected,
)
from stratbox.base.limits import BudgetMeter
from stratbox.data import ByteIdentity


class _LocalStage:
    def __init__(self, stream: BinaryIO, staging: Path, destination: Path, store: LocalFileStore):
        self.stream = stream
        self.staging = staging
        self.destination = destination
        self.store = store
        self.attempted = False

    def commit(self, mode: WriteMode, expected_revision: str | None) -> bool:
        if self.attempted:
            raise MutationRejected("Staged write already attempted")
        self.attempted = True
        try:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()
            target = self.store.checked_file_path(str(self.destination))
        except OSError as error:
            raise MutationRejected("Unable to finalize staging") from error
        if mode == "immutable":
            try:
                os.link(self.staging, target)
            except FileExistsError:
                return False
            except OSError as error:
                if error.errno in {ENOTSUP, EXDEV}:
                    raise MutationRejected("Atomic creation unavailable", capability_missing=True) from error
                raise
            # Removing the staging link also changes the destination inode's
            # ctime. Finish that transition before observing its revision.
            self.staging.unlink()
        elif mode == "replace_expected_revision":
            if not expected_revision:
                raise MutationRejected("Expected revision is required")
            with self.store.guard_directory(str(target.parent)):
                try:
                    actual = self.store.inspect_file(str(target))
                except FileNotFoundError:
                    return False
                if actual.revision != expected_revision:
                    return False
                os.replace(self.staging, target)
        elif mode == "best_effort_verified":
            os.replace(self.staging, target)
        else:
            raise MutationRejected("Unsupported write mode")
        return True


class LocalFileStore(FileStore):
    """Local paths with optional confinement to a caller-owned directory."""

    store_id = "local"

    def __init__(self, root: str | None = None):
        self._root = Path(root).expanduser().resolve() if root is not None else None

    def _abs(self, path: str) -> Path:
        candidate = Path(str(path).replace("\\", "/"))
        if self._root is None:
            return candidate
        candidate = candidate if candidate.is_absolute() else self._root / candidate
        if ".." in candidate.parts or not candidate.resolve().is_relative_to(
            self._root
        ):
            raise PermissionError("Path is outside the store root")
        return candidate

    def checked_file_path(self, path: str) -> Path:
        """Reject symlinks, including those in the parent chain."""
        candidate = self._abs(path).absolute()
        for component in (candidate, *candidate.parents):
            if (
                component.is_symlink()
                or getattr(component, "is_junction", lambda: False)()
            ):
                raise PermissionError(
                    "Symbolic file path is outside the write contract"
                )
        return candidate

    @contextmanager
    def stage_write(self, path: str):
        try:
            target = self.checked_file_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target = self.checked_file_path(str(target))
            fd, name = tempfile.mkstemp(prefix=".stratbox-", dir=target.parent)
        except OSError as error:
            raise MutationRejected("Storage destination is unavailable") from error
        staging = Path(name)
        try:
            with os.fdopen(fd, "w+b") as stream:
                yield _LocalStage(stream, staging, target, self)
        finally:
            staging.unlink(missing_ok=True)

    def create_if_absent(self, path: str, data: bytes) -> bool:
        with self.stage_write(path) as stage:
            stage.stream.write(data)
            return stage.commit("immutable", None)

    def replace_if_revision(self, path: str, data: bytes, expected_revision: str) -> bool:
        with self.stage_write(path) as stage:
            stage.stream.write(data)
            return stage.commit("replace_expected_revision", expected_revision)

    def write_bytes(self, path: str, data: bytes) -> None:
        with self.stage_write(path) as stage:
            stage.stream.write(data)
            stage.commit("best_effort_verified", None)

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
        st = p.lstat()
        return FileStat(
            path=str(path),
            is_file=stat.S_ISREG(st.st_mode),
            is_dir=stat.S_ISDIR(st.st_mode),
            is_symlink=stat.S_ISLNK(st.st_mode)
            or getattr(p, "is_junction", lambda: False)(),
            size=int(st.st_size),
            mtime=float(st.st_mtime),
            atime=float(st.st_atime),
            ctime=float(st.st_ctime),
        )

    def listdir(self, path: str) -> list[str]:
        return sorted(self.iter_names(path))

    def iter_names(self, path: str) -> Iterator[str]:
        with os.scandir(self._abs(path)) as entries:
            for entry in entries:
                yield entry.name

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

    # --- Оптимизированный walk (быстрее дефолтного) ---

    def walk(self, top: str) -> Iterator[Tuple[str, list[str], list[str]]]:
        top_p = self._abs(top)
        if not top_p.exists() or not top_p.is_dir():
            return

        def onerror(error: OSError) -> None:
            raise error

        for dirpath, dirnames, filenames in os.walk(top_p, onerror=onerror):
            dp = Path(dirpath)

            # Возвращаем пути "в координатах пользователя":
            # если root задан — стараемся сделать относительным к root.
            if self._root:
                try:
                    dp_rel = dp.relative_to(self._root)
                    dirpath_out = dp_rel.as_posix()
                except Exception:
                    dirpath_out = dp.as_posix()
            else:
                dirpath_out = dp.as_posix()

            yield dirpath_out, sorted(list(dirnames)), sorted(list(filenames))

    def directory_identity(self, path: str) -> str:
        directory = self.checked_file_path(path)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise MutationRejected("Expected a directory")
        namespace = f"{os.path.normcase(str(directory))}:{info.st_dev}:{info.st_ino}"
        return sha256(namespace.encode("utf-8")).hexdigest()

    @contextmanager
    def guard_directory(self, path: str):
        directory = self.checked_file_path(path)
        if not directory.is_dir():
            raise MutationRejected("Directory is unavailable")
        lock = directory / DIRECTORY_GUARD_NAME
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as error:
            raise MutationRejected("Directory guard is unavailable") from error
        try:
            os.close(fd)
            yield
        finally:
            lock.unlink(missing_ok=True)

    @staticmethod
    def _revision(info: os.stat_result) -> str:
        return f"{info.st_dev}:{info.st_ino}:{info.st_size}:{info.st_mtime_ns}:{info.st_ctime_ns}"

    def current_revision(self, path: str) -> str:
        info = self.checked_file_path(path).lstat()
        if not stat.S_ISREG(info.st_mode):
            raise MutationRejected("Expected a regular file")
        return self._revision(info)

    def storage_scope(self, path: str) -> str:
        return sha256(os.path.normcase(str(self.checked_file_path(path).resolve())).encode("utf-8")).hexdigest()

    def inspect_file(self, path: str) -> FileVersion:
        return self.inspect_file_budgeted(path, budget=None)

    def inspect_file_budgeted(
        self, path: str, *, budget: BudgetMeter | None,
        checkpoint: Callable[[], None] | None = None,
    ) -> FileVersion:
        candidate = self.checked_file_path(path)
        initial = candidate.lstat()
        if not stat.S_ISREG(initial.st_mode):
            raise MutationRejected("Expected a regular file")
        if budget is not None:
            budget.check("input_bytes", initial.st_size)
        digest = sha256()
        size = 0
        with candidate.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if self._revision(opened) != self._revision(initial):
                raise MutationRejected("File changed while opening it")
            while True:
                if checkpoint is not None:
                    checkpoint()
                chunk = stream.read(min(65536, initial.st_size - size + 1))
                if not chunk:
                    break
                if budget is not None:
                    budget.charge("input_bytes", len(chunk))
                digest.update(chunk)
                size += len(chunk)
                if size > initial.st_size:
                    raise MutationRejected("File grew while reading it")
            if (
                self._revision(os.fstat(stream.fileno())) != self._revision(initial)
                or self._revision(candidate.lstat()) != self._revision(initial)
                or size != initial.st_size
            ):
                raise MutationRejected("File changed while reading it")
        return FileVersion(
            path, self._revision(initial), ByteIdentity(digest.hexdigest(), size)
        )

    def remove_expected(self, expected: FileVersion) -> bool:
        if self.inspect_file(expected.path) != expected:
            return False
        source = self.checked_file_path(expected.path)
        source.unlink()
        if os.path.lexists(source):
            raise OSError("File removal could not be confirmed")
        return True

    def rename_expected(self, expected: FileVersion, target: str) -> bool:
        if self.inspect_file(expected.path) != expected:
            return False
        source = self.checked_file_path(expected.path)
        destination = self.checked_file_path(target)
        if source.parent != destination.parent:
            raise MutationRejected("Expected a same-directory move")
        before = source.lstat()
        if self._revision(before) != expected.revision:
            return False
        try:
            # A hard link commits the same inode without overwriting a target.
            # Only then may the old name be removed.
            os.link(source, destination, follow_symlinks=False)
        except FileExistsError:
            return False
        old = source.lstat()
        new = destination.lstat()
        if (old.st_dev, old.st_ino, old.st_size, old.st_mtime_ns) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) or (new.st_dev, new.st_ino) != (old.st_dev, old.st_ino):
            raise OSError("Move could not be confirmed")
        source.unlink()
        if (
            os.path.lexists(source)
            or self.inspect_file(target).identity != expected.identity
        ):
            raise OSError("Move could not be confirmed")
        return True
