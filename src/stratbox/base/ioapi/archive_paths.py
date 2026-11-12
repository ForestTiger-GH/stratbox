"""Bounded-memory ZIP creation from verified local files.

All selection and naming decisions belong to the calling domain. This module
handles only admission, byte streaming, source integrity and atomic publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from stratbox.data import ByteIdentity

from .archive_bytes import ArchiveError, safe_member_name

_CHUNK = 1024 * 1024
_MAX_FILES = 500
_MAX_BYTES = 64 * 1024 * 1024 * 1024  # 64 GiB, explicit safety bound
_MAX_EXTRA_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class PathArchiveEntry:
    path: Path
    name: str
    identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class PathArchiveReceipt:
    path: str
    identity: ByteIdentity
    member_names: tuple[str, ...]


def _no_symlinks(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
            raise ArchiveError("archive.symlink_forbidden")


def _digest_file(path: Path) -> ByteIdentity:
    digest = sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(_CHUNK):
            digest.update(chunk)
            total += len(chunk)
    return ByteIdentity(digest.hexdigest(), total)


def zip_paths(
    entries: tuple[PathArchiveEntry, ...],
    destination: Path,
    *,
    extras: Mapping[str, bytes] | None = None,
    compression: str = "stored",
) -> PathArchiveReceipt:
    """Write ZIP to a same-directory staging file, then publish atomically.

    O(chunk) RAM irrespective of input size. Each source is verified against
    its expected SHA-256 during the single streaming pass. The staged ZIP is
    checked before publication. An error leaves an existing output untouched.
    """
    if compression not in {"stored", "deflated"}:
        raise ArchiveError("archive.compression_invalid")
    additional = dict(extras or {})
    if not entries or len(entries) + len(additional) > _MAX_FILES:
        raise ArchiveError("archive.selection_invalid")
    names = [item.name for item in entries] + list(additional)
    if (len({name.casefold() for name in names}) != len(names)
        or any(not safe_member_name(name) or "/" in name or "\\" in name for name in names)):
        raise ArchiveError("archive.unsafe_member")
    if any(not isinstance(data, bytes) for data in additional.values()):
        raise ArchiveError("archive.extra_invalid")
    if sum(len(data) for data in additional.values()) > _MAX_EXTRA_BYTES:
        raise ArchiveError("archive.extra_too_large")
    if sum(item.identity.size for item in entries) > _MAX_BYTES:
        raise ArchiveError("archive.size_limit")

    destination = Path(destination).absolute()
    _no_symlinks(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _no_symlinks(destination)
    for item in entries:
        path = Path(item.path).absolute()
        _no_symlinks(path)
        if path == destination:
            raise ArchiveError("archive.source_destination_conflict")
        try:
            current = path.stat()
        except OSError:
            raise ArchiveError("archive.source_unavailable") from None
        if not stat.S_ISREG(current.st_mode) or current.st_size != item.identity.size:
            raise ArchiveError("archive.source_changed")

    temp_path = None
    try:
        fd, name = tempfile.mkstemp(prefix=".stratbox-zip-", suffix=".tmp", dir=destination.parent)
        temp_path = Path(name)
        with os.fdopen(fd, "w+b") as output:
            method = ZIP_STORED if compression == "stored" else ZIP_DEFLATED
            with ZipFile(output, "w", allowZip64=True, compression=method) as archive:
                for item in entries:
                    digest = sha256()
                    total = 0
                    info = ZipInfo(item.name)
                    info.compress_type = method
                    info.external_attr = 0o100644 << 16
                    with Path(item.path).open("rb") as source, archive.open(info, "w", force_zip64=True) as member:
                        opened = os.fstat(source.fileno())
                        if not stat.S_ISREG(opened.st_mode) or opened.st_size != item.identity.size:
                            raise ArchiveError("archive.source_changed")
                        while chunk := source.read(_CHUNK):
                            total += len(chunk)
                            if total > item.identity.size:
                                raise ArchiveError("archive.source_changed")
                            digest.update(chunk)
                            member.write(chunk)
                        final = os.fstat(source.fileno())
                    if (total != item.identity.size or digest.hexdigest() != item.identity.sha256
                        or opened.st_dev != final.st_dev or opened.st_ino != final.st_ino
                        or opened.st_size != final.st_size or opened.st_mtime_ns != final.st_mtime_ns):
                        raise ArchiveError("archive.source_changed")
                for name, data in additional.items():
                    info = ZipInfo(name)
                    info.compress_type = ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
            output.flush()
            os.fsync(output.fileno())
        # No archive expansion, no full payload in RAM: final on-disk receipt.
        digest = _digest_file(temp_path)
        if digest.size > _MAX_BYTES + _MAX_EXTRA_BYTES + 1024 * 1024 * len(names):
            raise ArchiveError("archive.size_limit")
        os.replace(temp_path, destination)
        temp_path = None
        return PathArchiveReceipt(str(destination), digest, tuple(names))
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, ArchiveError):
            raise
        raise ArchiveError("archive.write_failed") from error
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
