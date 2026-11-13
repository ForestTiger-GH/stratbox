"""Stream a verified archive through caller-selected read and commit capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import BinaryIO, Callable, Mapping
from unicodedata import normalize
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from stratbox.base.filestore import FileMutation, MutationRejected, SourceStore, StagedWriter, WriteMode
from stratbox.base.limits import BudgetMeter
from stratbox.data import ByteIdentity, StoredBytesReceipt, canonical_manifest_bytes

from .archive_bytes import ArchiveError, safe_member_name
from .bytes import file_identity

_CHUNK = 1024 * 1024
_MAX_FILES = 500
_MAX_BYTES = 64 * 1024**3
_MAX_EXTRA_BYTES = 8 * 1024**2


@dataclass(frozen=True, slots=True)
class ArchiveEntry:
    source: str
    name: str
    identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class PathArchiveReceipt:
    path: str
    identity: ByteIdentity
    member_names: tuple[str, ...]
    storage: StoredBytesReceipt
    effect_id: str


class _BoundedStage:
    def __init__(self, stream: BinaryIO, budget: BudgetMeter):
        self.stream = stream
        self.budget = budget
        self.high_water = 0

    def write(self, data: bytes) -> int:
        offset = self.stream.tell()
        end = offset + len(data)
        if end > self.high_water:
            self.budget.charge("temporary_bytes", end - self.high_water)
            self.high_water = end
        count = self.stream.write(data)
        if count != len(data):
            raise OSError("Short archive staging write")
        return count

    def seek(self, offset, whence=0):
        return self.stream.seek(offset, whence)

    def tell(self):
        return self.stream.tell()

    def flush(self):
        self.stream.flush()


def _copy_member(archive, entry, source_store, method, budget, checkpoint):
    info = ZipInfo(entry.name)
    info.compress_type = method
    info.external_attr = 0o100644 << 16
    digest = sha256()
    size = 0
    with source_store.open_read(entry.source) as source, archive.open(
        info, "w", force_zip64=True
    ) as member:
        while True:
            checkpoint()
            chunk = source.read(min(_CHUNK, entry.identity.size - size + 1))
            if not chunk:
                break
            size += len(chunk)
            budget.charge("input_bytes", len(chunk))
            if size > entry.identity.size:
                raise ArchiveError("archive.source_changed")
            digest.update(chunk)
            member.write(chunk)
    if ByteIdentity(digest.hexdigest(), size) != entry.identity:
        raise ArchiveError("archive.source_changed")


def _digest(stream, checkpoint) -> ByteIdentity:
    stream.seek(0)
    digest = sha256()
    size = 0
    while True:
        checkpoint()
        chunk = stream.read(_CHUNK)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    return ByteIdentity(digest.hexdigest(), size)


def zip_to_store(
    entries: tuple[ArchiveEntry, ...], destination: str, *,
    source_store: SourceStore, output_store: StagedWriter, budget: BudgetMeter,
    checkpoint: Callable[[], None], mode: WriteMode = "immutable",
    expected_revision: str | None = None, extras: Mapping[str, bytes] | None = None,
    compression: str = "stored", plan_identity: ByteIdentity | None = None,
    operation_id: str | None = None, require_admission: bool = False,
    source_directory: str | None = None,
) -> PathArchiveReceipt:
    """Verify a private ZIP, commit conditionally and read the actual destination."""
    if compression not in {"stored", "deflated"}:
        raise ArchiveError("archive.compression_invalid")
    guarantees = {
        "immutable": "atomic_create", "replace_expected_revision": "compare_and_replace",
        "best_effort_verified": "read_back",
    }
    if mode not in guarantees or (mode == "replace_expected_revision" and not expected_revision):
        raise ArchiveError("effect.mode_invalid")
    if not callable(getattr(output_store, "stage_write", None)):
        raise ArchiveError("provider.capability_missing")
    additional = dict(extras or {})
    names = tuple(item.name for item in entries) + tuple(additional)
    if not entries or len(names) > _MAX_FILES:
        raise ArchiveError("archive.selection_invalid")
    if (
        len({normalize("NFC", name).casefold() for name in names}) != len(names)
        or any(not safe_member_name(name) or "/" in name or "\\" in name for name in names)
    ):
        raise ArchiveError("archive.unsafe_member")
    if any(not isinstance(data, bytes) for data in additional.values()):
        raise ArchiveError("archive.extra_invalid")
    if sum(map(len, additional.values())) > _MAX_EXTRA_BYTES or sum(
        item.identity.size for item in entries
    ) > _MAX_BYTES:
        raise ArchiveError("archive.size_limit")
    if source_store is output_store and any(item.source == destination for item in entries):
        raise ArchiveError("archive.source_destination_conflict")
    local_source = getattr(source_store, "checked_file_path", None)
    local_destination = getattr(output_store, "checked_file_path", None)
    if callable(local_source) and callable(local_destination):
        target = local_destination(destination)
        if any(local_source(item.source) == target for item in entries):
            raise ArchiveError("archive.source_destination_conflict")
    budget.charge("objects", len(names))
    budget.check("input_bytes", sum(item.identity.size for item in entries))
    store_id = getattr(output_store, "store_id", type(output_store).__name__)
    identity = None
    effect_id = None

    def receipt(status, code=None, *, stage="verify", actual=None):
        return PathArchiveReceipt(destination, identity, names, StoredBytesReceipt(
            destination, identity, status, guarantees[mode], store_id, code,
            stage=stage, observed_identity=actual, expected_revision=expected_revision,
            effect_id=effect_id,
        ), effect_id)

    attempted = False
    try:
        with output_store.stage_write(destination) as stage:
            method = ZIP_STORED if compression == "stored" else ZIP_DEFLATED
            with ZipFile(_BoundedStage(stage.stream, budget), "w", compression=method) as archive:
                for entry in entries:
                    _copy_member(archive, entry, source_store, method, budget, checkpoint)
                for name, data in additional.items():
                    checkpoint()
                    info = ZipInfo(name)
                    info.compress_type = ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            stage.stream.flush()
            identity = _digest(stage.stream, checkpoint)
            budget.charge("output_bytes", identity.size)
            effect_id = ByteIdentity.of(canonical_manifest_bytes({
                "plan": plan_identity.sha256 if plan_identity else None, "destination": destination,
                "operation": operation_id, "mode": mode, "revision": expected_revision,
                "payload": identity.sha256,
            })).sha256
            checkpoint()
            if require_admission and (
                operation_id is None or plan_identity is None
                or not callable(getattr(stage, "commit_admitted", None))
            ):
                return receipt("failed", "provider.capability_missing", stage="preflight")
            attempted = True
            try:
                if require_admission:
                    committed = stage.commit_admitted(FileMutation(
                        operation_id, effect_id, plan_identity, "write",
                        directory=source_directory, destination=destination, content=identity, mode=mode,
                        expected_revision=expected_revision,
                    ))
                else:
                    committed = stage.commit(mode, expected_revision)
            except MutationRejected as error:
                return receipt("failed", "provider.capability_missing" if error.capability_missing
                               else "effect.rejected", stage="commit")
            if type(committed) is not bool:
                return receipt("unknown", "effect.outcome_unknown", stage="commit")
            if not committed and mode != "immutable":
                return receipt("failed", "effect.conflict", stage="commit")
            try:
                actual = file_identity(destination, store=output_store, limit=identity.size,
                                       checkpoint=checkpoint)
            except ValueError:
                actual = None
            except Exception:
                return receipt("unknown", "effect.read_back_unavailable")
            if actual != identity:
                return receipt("unknown" if committed else "failed",
                               "effect.read_back_mismatch" if committed else "effect.conflict",
                               actual=actual)
            return receipt("stored" if committed else "already_present", actual=actual)
    except Exception:
        if attempted:
            return receipt("unknown", "effect.outcome_unknown", stage="commit")
        raise
