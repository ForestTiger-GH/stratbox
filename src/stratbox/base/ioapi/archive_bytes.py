"""Bounded, in-memory archive inspection, extraction and creation."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath, PureWindowsPath
from stat import S_IFDIR, S_IFMT, S_IFREG
from typing import BinaryIO, Callable, ContextManager, Iterator, Mapping, Protocol
from unicodedata import normalize
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


from stratbox.base.limits import BudgetExceeded, BudgetMeter


class ArchiveError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    members: int = 250
    unpacked_bytes: int = 100_000_000
    member_bytes: int = 32_000_000
    packed_bytes: int = 32_000_000

    def __post_init__(self) -> None:
        if (
            min(self.members, self.unpacked_bytes, self.member_bytes, self.packed_bytes)
            < 1
        ):
            raise ValueError("Archive limits must be positive")


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    name: str
    size: int
    directory: bool = False
    regular: bool = True
    encrypted: bool = False


class ArchiveContents(Protocol):
    def members(self) -> tuple[ArchiveMember, ...]: ...
    def open(self, name: str) -> ContextManager[BinaryIO]: ...


class ArchiveReader(Protocol):
    def open(self, data: bytes) -> ContextManager[ArchiveContents]: ...


def safe_member_name(name: str) -> bool:
    path = name.replace("\\", "/").rstrip("/")
    return (
        0 < len(path) <= 512
        and not path.startswith("/")
        and ":" not in path
        and not PureWindowsPath(path).drive
        and not PurePosixPath(path).is_absolute()
        and not any(part in {"", ".", ".."} for part in path.split("/"))
        and not any(ord(char) < 32 or ord(char) == 127 for char in path)
    )


def validate_members(members: tuple[ArchiveMember, ...], limits: ArchiveLimits) -> None:
    if (
        not 0 < len(members) <= limits.members
        or sum(member.size for member in members) > limits.unpacked_bytes
        or any(not 0 <= member.size <= limits.member_bytes for member in members)
    ):
        raise ArchiveError("archive.size_limit")
    names = [
        normalize("NFC", member.name.replace("\\", "/").rstrip("/")).casefold()
        for member in members
    ]
    if len(set(names)) != len(names) or any(
        not safe_member_name(member.name) or member.encrypted or not member.regular
        for member in members
    ):
        raise ArchiveError("archive.unsafe_member")


def zip_members(archive: ZipFile) -> tuple[ArchiveMember, ...]:
    return tuple(
        ArchiveMember(
            info.orig_filename,
            info.file_size,
            info.is_dir(),
            S_IFMT(info.external_attr >> 16) in {0, S_IFREG, S_IFDIR},
            bool(info.flag_bits & 1),
        )
        for info in archive.infolist()
    )


@contextmanager
def open_zip(
    data: bytes, limits: ArchiveLimits = ArchiveLimits(), *,
    budget: BudgetMeter | None = None, depth: int = 1,
) -> Iterator[ZipFile]:
    if not 1 <= depth <= 4:
        raise ArchiveError("archive.depth_limit")
    if budget is not None:
        budget.check("archive_depth", depth)
    if len(data) > limits.packed_bytes:
        raise ArchiveError("archive.size_limit")
    try:
        with ZipFile(BytesIO(data)) as archive:
            members = zip_members(archive)
            validate_members(members, limits)
            if budget is not None:
                budget.charge("objects", len(members))
            yield archive
    except BudgetExceeded:
        raise
    except (BadZipFile, EOFError, NotImplementedError, RuntimeError) as error:
        raise ArchiveError("archive.invalid_zip") from error


class _RarContents:
    def __init__(self, archive):
        self.archive = archive

    def members(self) -> tuple[ArchiveMember, ...]:
        return tuple(
            ArchiveMember(
                info.filename,
                info.file_size,
                info.is_dir(),
                (info.is_file() or info.is_dir())
                and not info.is_symlink()
                and getattr(info, "file_redir", None) is None,
                info.needs_password(),
            )
            for info in self.archive.infolist()
        )

    def open(self, name: str):
        return self.archive.open(name)


class RarArchiveReader:
    """Optional rarfile adapter. Compressed members require a supported system extractor."""

    @contextmanager
    def open(self, data: bytes):
        from stratbox.base.utils.optional_deps import require_extra

        rarfile = require_extra("rarfile", "rar")
        try:
            with rarfile.RarFile(BytesIO(data)) as archive:
                yield _RarContents(archive)
        except rarfile.RarCannotExec as error:
            raise ArchiveError("archive.rar_extractor_unavailable") from error
        except (rarfile.Error, OSError, EOFError) as error:
            raise ArchiveError("archive.invalid_rar") from error


def _read_member(
    open_member, member: ArchiveMember, budget: BudgetMeter | None = None,
    checkpoint: Callable[[], None] | None = None,
) -> bytes:
    data = bytearray()
    with open_member(member.name) as stream:
        while True:
            if checkpoint is not None:
                checkpoint()
            if budget is not None:
                budget.checkpoint()
            chunk = stream.read(min(65536, member.size - len(data) + 1))
            if not chunk:
                break
            if budget is not None:
                budget.charge("decoded_bytes", len(chunk))
            data.extend(chunk)
            if len(data) > member.size:
                raise ArchiveError("archive.member_size_mismatch")
    if len(data) != member.size:
        raise ArchiveError("archive.member_size_mismatch")
    return bytes(data)


def _selected_members(
    members: tuple[ArchiveMember, ...],
    select: Callable[[tuple[str, ...]], tuple[str, ...]],
) -> tuple[ArchiveMember, ...]:
    available = {member.name: member for member in members if not member.directory}
    selected = select(tuple(available))
    if len(set(selected)) != len(selected) or any(
        name not in available for name in selected
    ):
        raise ArchiveError("archive.selection_invalid")
    return tuple(available[name] for name in selected)


def extract_members(
    data: bytes,
    *,
    select: Callable[[tuple[str, ...]], tuple[str, ...]],
    limits: ArchiveLimits = ArchiveLimits(),
    rar_reader: ArchiveReader | None = None,
    budget: BudgetMeter | None = None,
    depth: int = 1,
    checkpoint: Callable[[], None] | None = None,
) -> dict[str, bytes]:
    if not 1 <= depth <= 4:
        raise ArchiveError("archive.depth_limit")
    if budget is not None:
        budget.check("archive_depth", depth)
    if len(data) > limits.packed_bytes:
        raise ArchiveError("archive.size_limit")
    if data.startswith(b"Rar!"):
        if rar_reader is None:
            raise ArchiveError("archive.rar_provider_missing")
        with rar_reader.open(data) as contents:
            members = contents.members()
            validate_members(members, limits)
            if budget is not None:
                budget.charge("objects", len(members))
            return {
                member.name: _read_member(contents.open, member, budget, checkpoint)
                for member in _selected_members(members, select)
            }
    if not data.startswith(b"PK"):
        raise ArchiveError("archive.format_unsupported")
    with open_zip(data, limits, budget=budget, depth=depth) as archive:
        return {
            member.name: _read_member(archive.open, member, budget, checkpoint)
            for member in _selected_members(zip_members(archive), select)
        }


def zip_bytes(
    files: Mapping[str, bytes], *, limits: ArchiveLimits = ArchiveLimits()
) -> bytes:
    validate_members(
        tuple(ArchiveMember(name, len(data)) for name, data in files.items()), limits
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            info = ZipInfo(name)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    if buffer.tell() > limits.packed_bytes:
        raise ArchiveError("archive.size_limit")
    return buffer.getvalue()
