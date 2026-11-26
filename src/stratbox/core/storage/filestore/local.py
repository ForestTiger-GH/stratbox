"""Local file and directory commands."""

from __future__ import annotations

from contextlib import contextmanager
from errno import ENOTSUP, EXDEV
from hashlib import sha256
import os
import re
import stat
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, Callable, Iterator, Tuple
from urllib.parse import unquote, urlsplit

from stratbox.core.storage.filestore.ports import FileStore, WriteMode
from stratbox.core.storage.filestore.types import (
    DIRECTORY_GUARD_NAME,
    FileStat,
    FileVersion,
    MutationRejected,
)
from stratbox.core.limits import BudgetMeter
from stratbox.shared.identity import ByteIdentity


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
            if mode != "immutable": self.store._mutable(target)
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


class _ContentStage:
    """One private file becomes immutable content only after its hash is known."""
    def __init__(self, stage, store, directory):
        self._stage, self._store, self.directory = stage, store, directory
        self.stream = stage.stream

    def location(self, identity):
        return str(Path(self.directory) / identity.sha256)

    def commit(self, identity, *, checkpoint=None):
        digest, size = sha256(), 0
        self.stream.flush(); self.stream.seek(0)
        while chunk := self.stream.read(65536):
            if checkpoint: checkpoint()
            digest.update(chunk); size += len(chunk)
        if ByteIdentity(digest.hexdigest(), size) != identity:
            raise MutationRejected("Stream identity mismatch", code="storage.identity_mismatch")
        location = self.location(identity)
        self._stage.destination = self._store.checked_file_path(location)
        created = self._stage.commit("immutable", None)
        if not created and self._store.inspect_file(location).identity != identity:
            raise MutationRejected("Immutable content conflict", code="storage.immutable_conflict")
        return location


class LocalFileStore(FileStore):
    """Local paths with optional confinement to a caller-owned directory."""

    store_id = "local"

    def __init__(self, root: str | None = None):
        self._root = Path(root).expanduser().resolve() if root is not None else None

    def _mutable(self, path):
        if Path(path).name == DIRECTORY_GUARD_NAME or ".stratbox-transitions" in Path(path).parts:
            raise MutationRejected("Provider transition evidence is protected", code="storage.provider_state_protected")
        if re.fullmatch(r"[a-f0-9]{64}", Path(path).name):
            raise MutationRejected("Retained content member is protected", code="storage.immutable_member")

    def validate_named_destination(self, path):
        self._mutable(self.checked_file_path(path))

    def _abs(self, path: str) -> Path:
        value = str(path).replace("\\", "/")
        if value[:7].casefold() == "file://":
            parts = urlsplit(value)
            if "?" in value or "#" in value or not parts.path:
                raise ValueError("Invalid file URI")
            value = unquote(parts.path, errors="strict").replace("\\", "/")
            if parts.netloc and parts.netloc.casefold() != "localhost":
                if os.name != "nt":
                    raise ValueError("File URI requires a locally mounted path")
                if re.fullmatch(r"[A-Za-z]:", parts.netloc):
                    value = parts.netloc + value
                elif re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", parts.netloc):
                    value = "//" + parts.netloc + value
                else:
                    raise ValueError("Invalid UNC host")
            elif os.name == "nt" and re.match(r"^/[A-Za-z]:(?:/|$)", value):
                value = value[1:]
        elif re.match(r"^[A-Za-z][A-Za-z0-9+.-]+://", value):
            raise ValueError("Expected a filesystem path")
        if os.name != "nt" and (re.match(r"^/?[A-Za-z]:(?:/|$)", value) or value.startswith("//")):
            raise ValueError("Windows path requires a mapped filesystem")
        candidate = Path(value)
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
        p = self.checked_file_path(path)
        self._mutable(p)
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
        target = self.checked_file_path(path)
        self._mutable(target)
        target.unlink()

    def rmdir(self, path: str) -> None:
        self._abs(path).rmdir()

    def rmtree(self, path: str) -> None:
        target = self.checked_file_path(path)
        if any(re.fullmatch(r"[a-f0-9]{64}", item.name) for item in target.rglob("*")):
            raise MutationRejected("Directory contains retained content", code="storage.immutable_member")
        shutil.rmtree(target)

    def rename(self, src: str, dst: str) -> None:
        src_p = self.checked_file_path(src)
        dst_p = self.checked_file_path(dst)
        self._mutable(src_p); self._mutable(dst_p)
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
        self._mutable(expected.path)
        if self.inspect_file(expected.path) != expected:
            return False
        source = self.checked_file_path(expected.path)
        source.unlink()
        if os.path.lexists(source):
            raise OSError("File removal could not be confirmed")
        return True

    def rename_expected(self, expected: FileVersion, target: str) -> bool:
        self._mutable(expected.path); self._mutable(target)
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

    def _named_transition_path(self, effect_id, intent):
        if not isinstance(effect_id, str) or re.fullmatch(r"[a-f0-9]{64}", effect_id) is None:
            raise MutationRejected("Qualified effect identity is required", code="storage.transition_identity_invalid")
        source = self.checked_file_path(intent.source)
        return source.parent / ".stratbox-transitions" / effect_id[:2] / effect_id[2:4] / (effect_id + ".json")

    def _named_intent_scope(self, intent):
        from stratbox.shared.data.values import fingerprint
        scope = lambda path: fingerprint((str(self.provider_id), str(self.storage_scope(path))))
        return (intent.provider_scope == scope(intent.destination)
                and intent.source_provider_scope == scope(intent.source))

    def apply_named_mutation(self, effect_id, intent, *, checkpoint=lambda: None):
        """Conditionally move/delete and retain a bounded provider observation.

        The directory guard covers participating writers. A crash after the
        mutation but before the observation is durable remains unresolved; path
        absence alone is deliberately insufficient for later confirmation.
        """
        import json
        from stratbox.shared.data.materials import NamedEffectIntent, NamedMaterialReceipt
        from stratbox.shared.data.values import canonical_tree
        if (not isinstance(intent, NamedEffectIntent) or intent.operation not in {"move", "delete"}
                or not intent.expected_source_revision or intent.policy != "create_only"
                or not self._named_intent_scope(intent)):
            raise MutationRejected("Exact transition intent is required", code="storage.transition_intent_invalid")
        source, destination = self.checked_file_path(intent.source), self.checked_file_path(intent.destination)
        if (intent.operation == "move" and (source == destination or source.parent != destination.parent)
                or intent.operation == "delete" and source != destination):
            raise MutationRejected("Transition paths conflict", code="storage.transition_path_invalid")
        if (intent.operation == "move" and intent.identity != intent.expected_source
                or intent.operation == "delete" and intent.identity is not None):
            raise MutationRejected("Transition identity conflicts", code="storage.transition_intent_invalid")
        proof_path = self._named_transition_path(effect_id, intent)
        result = NamedMaterialReceipt(intent.destination, intent.identity, intent.provider_scope,
            operation=intent.operation, guarantee="guarded_conditional_transition")
        raw = json.dumps({"effect_id": effect_id, "intent": canonical_tree(intent),
            "receipt": canonical_tree(result)}, sort_keys=True, separators=(",", ":")).encode()
        if len(raw) > 1024 * 1024:
            raise MutationRejected("Transition evidence exceeds limit", code="storage.transition_metadata_limit")
        with self.guard_directory(str(source.parent)):
            checkpoint()
            observed = self.inspect_file_budgeted(intent.source, budget=None, checkpoint=checkpoint)
            if observed.identity != intent.expected_source or observed.revision != intent.expected_source_revision:
                raise MutationRejected("Source changed", code="maintenance.state_conflict")
            success = self.rename_expected(observed, intent.destination) if intent.operation == "move" else self.remove_expected(observed)
            if not success:
                raise MutationRejected("Conditional mutation rejected", code="maintenance.state_conflict")
            try:
                checkpoint()
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                self.create_if_absent(str(proof_path), raw)
                with proof_path.open("rb") as proof:
                    if proof.read(1024 * 1024 + 1) != raw:
                        raise OSError("Provider transition observation conflicts")
            except Exception as error:
                # Mutation already happened. Even a rejected proof write cannot
                # turn an uncertain acknowledgement into a known non-mutation.
                raise OSError("Transition acknowledgement is unavailable") from error
        return result

    def inspect_named_transition(self, effect_id, intent):
        """Read bounded provider evidence; the command verifies current paths."""
        import json
        from stratbox.shared.data.materials import NamedMaterialReceipt
        from stratbox.shared.data.values import restore_tree
        if not self._named_intent_scope(intent):
            return None
        path = self._named_transition_path(effect_id, intent)
        try:
            with self.checked_file_path(str(path)).open("rb") as stream:
                raw = stream.read(1024 * 1024 + 1)
        except FileNotFoundError:
            return None
        if len(raw) > 1024 * 1024:
            raise ValueError("storage.transition_metadata_limit")
        data = json.loads(raw)
        if (set(data) != {"effect_id", "intent", "receipt"} or data["effect_id"] != effect_id
                or restore_tree(data["intent"]) != intent):
            raise ValueError("storage.transition_evidence_conflict")
        receipt = restore_tree(data["receipt"])
        if (not isinstance(receipt, NamedMaterialReceipt) or receipt.operation != intent.operation
                or receipt.destination != intent.destination or receipt.identity != intent.identity
                or receipt.provider_scope != intent.provider_scope or receipt.status != "confirmed"
                or receipt.guarantee != "guarded_conditional_transition"):
            raise ValueError("storage.transition_evidence_conflict")
        return receipt


    provider_id = "local.files"
    immutable_content = True

    def open(self, location, mode="rb"):
        if mode != "rb":
            raise ValueError("storage.use_explicit_mutation")
        return self.open_read(location)

    def list(self, location):
        result = []
        for name in self.listdir(location):
            path = str(Path(location) / name)
            info = self.stat(path)
            if info.is_file:
                result.append({"path": path, "filename": name, "size": info.size, "mtime": info.mtime})
        return tuple(result)

    def create_immutable(self, location, data):
        from hashlib import sha256
        if re.fullmatch(r"[a-f0-9]{64}", Path(location).name) and Path(location).name != sha256(data).hexdigest():
            raise MutationRejected("Content address mismatch", code="storage.identity_mismatch")
        self.makedirs(str(Path(location).parent))
        created = self.create_if_absent(location, data)
        if not created and self.read_bytes(location) != data:
            raise MutationRejected("Immutable content conflict", code="storage.immutable_conflict")
        return sha256(data).hexdigest()

    @contextmanager
    def stage_content(self, directory):
        self.makedirs(directory)
        with self.stage_write(str(Path(directory) / ".incoming")) as stage:
            yield _ContentStage(stage, self, directory)

    def compare_and_set(self, location, expected_token, data):
        from hashlib import sha256
        target = self._abs(location)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.guard_directory(str(target.parent)):
            current = sha256(target.read_bytes()).hexdigest() if target.exists() else None
            if current != expected_token:
                raise MutationRejected("Publication state changed", code="storage.state_conflict")
            with self.stage_write(str(target)) as stage:
                stage.stream.write(data)
                stage.commit("best_effort_verified", None)
            return sha256(data).hexdigest()

    def move(self, source, destination):
        if len(Path(source).name) == 64:
            raise MutationRejected("Retained content member is protected", code="storage.immutable_member")
        return self.rename(source, destination)

    def delete(self, source):
        if len(Path(source).name) == 64:
            raise MutationRejected("Retained content member is protected", code="storage.immutable_member")
        return self.remove(source)
