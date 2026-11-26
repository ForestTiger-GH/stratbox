"""Stream a verified archive through caller-selected read and commit capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from contextlib import contextmanager
from typing import BinaryIO, Callable, Mapping
from unicodedata import normalize
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from stratbox.core.storage.filestore import SourceStore, StagedWriter, WriteMode
from stratbox.core.limits import BudgetMeter
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import StoredBytesReceipt

from stratbox.core.formats.archives.members import ArchiveError, safe_member_name, ArchiveLimits, open_zip_stream
from stratbox.core.storage.staging import BoundedStage, WRITE_GUARANTEES, commit_staged, stream_identity

_CHUNK = 1024 * 1024

@dataclass(frozen=True, slots=True)
class ArchiveWriteLimits:
    """Bounded packaging policy, independent of a source's table layout."""
    members: int = 10_000
    input_bytes: int = 64 * 1024**3
    extra_bytes: int = 8 * 1024**2
    nested_paths: bool = True

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in
               (self.members, self.input_bytes, self.extra_bytes)) or type(self.nested_paths) is not bool:
            raise ValueError("archive.limits_invalid")


def validate_output_names(names: tuple[str, ...], *, nested_paths: bool = True) -> None:
    """Use portable relative POSIX paths and reject aliases and file parents."""
    if any(not isinstance(name, str) or not safe_member_name(name) or
           "\\" in name or name.endswith("/") or (not nested_paths and "/" in name)
           for name in names):
        raise ArchiveError("archive.unsafe_member")
    normalized = tuple(normalize("NFC", name).casefold() for name in names)
    members = set(normalized)
    if len(members) != len(names) or any(
        "/".join(name.split("/")[:i]) in members
        for name in normalized for i in range(1, len(name.split("/")))
    ):
        raise ArchiveError("archive.unsafe_member")


@dataclass(frozen=True, slots=True)
class ArchiveEntry:
    source: object
    name: str
    identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class PathArchiveReceipt:
    path: str
    identity: ByteIdentity
    member_names: tuple[str, ...]
    storage: StoredBytesReceipt
    effect_id: str


@dataclass(frozen=True, slots=True)
class ArchiveEncodingEvidence:
    identity: ByteIdentity
    members: tuple[tuple[str, ByteIdentity], ...]
    compression: str


def _copy_member(archive, entry, open_member, method, checkpoint, budget=None):
    info = ZipInfo(entry.name)
    info.compress_type = method
    info.external_attr = 0o100644 << 16
    digest = sha256()
    size = 0
    with open_member(entry.source) as source, archive.open(
        info, "w", force_zip64=True
    ) as member:
        while True:
            checkpoint()
            chunk = source.read(min(_CHUNK, entry.identity.size - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if budget is not None:
                budget.checkpoint()
            if size > entry.identity.size:
                raise ArchiveError("archive.source_changed")
            digest.update(chunk)
            member.write(chunk)
    if ByteIdentity(digest.hexdigest(), size) != entry.identity:
        raise ArchiveError("archive.source_changed")


class _BoundedZipSink:
    def __init__(self, stream, limit):
        self.stream, self.limit = stream, limit

    def write(self, data):
        if self.stream.tell() + len(data) > self.limit:
            raise ArchiveError("archive.output_limit")
        if self.stream.write(data) != len(data):
            raise ArchiveError("archive.short_write")
        return len(data)

    def __getattr__(self, name):
        return getattr(self.stream, name)


def encode_zip(
    entries: tuple[ArchiveEntry, ...], sink: BinaryIO, *, open_member,
    compression: str = "deflated", limits: ArchiveWriteLimits = ArchiveWriteLimits(),
    max_output_bytes: int = 64 * 1024**3, checkpoint=lambda: None, budget=None,
    deterministic: bool = True,
) -> ArchiveEncodingEvidence:
    """Encode and verify complete bytes without creating any persistent effect.

    The caller owns the sink and its lifetime. Both buffered and staged command
    placements use this kernel. Entry order is caller order; fixed ZIP metadata
    makes identical ordered inputs reproducible in the same codec environment.
    """
    entries = tuple(entries)
    if (compression not in {"stored", "deflated"} or type(deterministic) is not bool):
        raise ArchiveError("archive.compression_invalid")
    if (not isinstance(limits, ArchiveWriteLimits) or type(max_output_bytes) is not int
            or max_output_bytes < 1 or len(entries) > limits.members
            or any(not isinstance(entry, ArchiveEntry) or not isinstance(entry.identity, ByteIdentity)
                   for entry in entries)):
        raise ArchiveError("archive.selection_invalid")
    validate_output_names(tuple(entry.name for entry in entries), nested_paths=limits.nested_paths)
    if sum(entry.identity.size for entry in entries) > limits.input_bytes:
        raise ArchiveError("archive.size_limit")
    if sink.tell() != 0:
        raise ArchiveError("archive.empty_sink_required")
    sink.seek(0, 2)
    if sink.tell():
        raise ArchiveError("archive.empty_sink_required")
    sink.seek(0)
    if budget is not None:
        budget.charge("objects", len(entries))
    method = ZIP_STORED if compression == "stored" else ZIP_DEFLATED
    with ZipFile(_BoundedZipSink(sink, max_output_bytes), "w", compression=method, allowZip64=True) as archive:
        for entry in entries:
            checkpoint()
            _copy_member(archive, entry, open_member, method, checkpoint, budget)
    sink.flush()
    size = sink.seek(0, 2)
    read_limits = ArchiveLimits(max(1, limits.members), max(1, limits.input_bytes),
        max(1, max((entry.identity.size for entry in entries), default=0)), max_output_bytes)
    with open_zip_stream(sink, size, read_limits) as archive:
        if tuple(archive.namelist()) != tuple(entry.name for entry in entries):
            raise ArchiveError("archive.verification_failed")
        for entry in entries:
            with archive.open(entry.name) as member:
                digest, length = sha256(), 0
                while True:
                    checkpoint()
                    chunk = member.read(min(_CHUNK, entry.identity.size - length + 1))
                    if not chunk:
                        break
                    length += len(chunk)
                    if length > entry.identity.size:
                        raise ArchiveError("archive.verification_failed")
                    digest.update(chunk)
                if ByteIdentity(digest.hexdigest(), length) != entry.identity:
                    raise ArchiveError("archive.verification_failed")
    identity = stream_identity(sink, checkpoint)
    return ArchiveEncodingEvidence(identity, tuple((entry.name, entry.identity) for entry in entries), compression)


def zip_to_store(
    entries: tuple[ArchiveEntry, ...], destination: str, *,
    source_store: SourceStore, output_store: StagedWriter, budget: BudgetMeter,
    checkpoint: Callable[[], None], mode: WriteMode = "immutable",
    expected_revision: str | None = None, extras: Mapping[str, bytes] | None = None,
    compression: str = "stored", plan_identity: ByteIdentity | None = None,
    operation_id: str | None = None, require_admission: bool = False,
    source_directory: str | None = None,
    on_effect: Callable[[StoredBytesReceipt], None] | None = None,
    limits: ArchiveWriteLimits = ArchiveWriteLimits(),
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
    if not isinstance(limits, ArchiveWriteLimits):
        raise ArchiveError("archive.limits_invalid")
    if not entries or len(names) > limits.members:
        raise ArchiveError("archive.selection_invalid")
    validate_output_names(names, nested_paths=limits.nested_paths)
    if any(not isinstance(data, bytes) for data in additional.values()):
        raise ArchiveError("archive.extra_invalid")
    if sum(map(len, additional.values())) > limits.extra_bytes or sum(
        item.identity.size for item in entries
    ) > limits.input_bytes:
        raise ArchiveError("archive.size_limit")
    if source_store is output_store and any(item.source == destination for item in entries):
        raise ArchiveError("archive.source_destination_conflict")
    source_scope = getattr(source_store, "storage_scope", None)
    output_scope = getattr(output_store, "storage_scope", None)
    if callable(source_scope) and callable(output_scope):
        target_scope = output_scope(destination)
        if any(source_scope(entry.source) == target_scope for entry in entries):
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
            @contextmanager
            def open_member(value):
                if isinstance(value, bytes):
                    with BytesIO(value) as stream:
                        yield stream
                else:
                    with source_store.open_read(value) as stream:
                        yield stream
            all_entries = (*entries, *(ArchiveEntry(data, name, ByteIdentity.of(data))
                                      for name, data in additional.items()))
            budget.charge("input_bytes", sum(item.identity.size for item in entries))
            encoded = encode_zip(all_entries, BoundedStage(stage.stream, budget),
                open_member=open_member, compression=compression, limits=ArchiveWriteLimits(
                    limits.members, limits.input_bytes + limits.extra_bytes,
                    limits.extra_bytes, limits.nested_paths), checkpoint=checkpoint)
            stage.stream.flush()
            identity = encoded.identity
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
