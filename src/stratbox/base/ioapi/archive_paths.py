"""Stream a verified archive through caller-selected read and commit capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Mapping
from unicodedata import normalize
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from stratbox.base.filestore import SourceStore, StagedWriter, WriteMode
from stratbox.base.limits import BudgetMeter
from stratbox.data import ByteIdentity, StoredBytesReceipt

from .archive_bytes import ArchiveError, safe_member_name
from .staging import BoundedStage, WRITE_GUARANTEES, commit_staged, stream_identity

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


def zip_to_store(
    entries: tuple[ArchiveEntry, ...], destination: str, *,
    source_store: SourceStore, output_store: StagedWriter, budget: BudgetMeter,
    checkpoint: Callable[[], None], mode: WriteMode = "immutable",
    expected_revision: str | None = None, extras: Mapping[str, bytes] | None = None,
    compression: str = "stored", plan_identity: ByteIdentity | None = None,
    operation_id: str | None = None, require_admission: bool = False,
    source_directory: str | None = None,
    on_effect: Callable[[StoredBytesReceipt], None] | None = None,
) -> PathArchiveReceipt:
    """Verify a private ZIP, commit conditionally and read the actual destination."""
    if compression not in {"stored", "deflated"}:
        raise ArchiveError("archive.compression_invalid")
    if mode not in WRITE_GUARANTEES or (mode == "replace_expected_revision" and not expected_revision):
        raise ArchiveError("effect.mode_invalid")
    if not destination or destination in {".", ".."} or "\x00" in destination:
        raise ArchiveError("effect.destination_invalid")
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
    result = None
    try:
        with output_store.stage_write(destination) as stage:
            method = ZIP_STORED if compression == "stored" else ZIP_DEFLATED
            with ZipFile(BoundedStage(stage.stream, budget), "w", compression=method) as archive:
                for entry in entries:
                    _copy_member(archive, entry, source_store, method, budget, checkpoint)
                for name, data in additional.items():
                    checkpoint()
                    info = ZipInfo(name)
                    info.compress_type = ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            stage.stream.flush()
            identity = stream_identity(stage.stream, checkpoint)
            storage = commit_staged(
                stage, destination, identity, store=output_store, budget=budget, checkpoint=checkpoint,
                mode=mode, expected_revision=expected_revision, plan_identity=plan_identity,
                operation_id=operation_id, require_admission=require_admission,
                source_directory=source_directory, on_effect=on_effect,
            )
            result = PathArchiveReceipt(destination, identity, names, storage, storage.effect_id)
    except OSError:
        if result is None:
            raise
    return result
