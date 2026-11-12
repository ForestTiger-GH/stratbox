"""RAR format commands using an explicitly selected archive reader."""

from stratbox.base.filestore import FileStore

from .archive_bytes import ArchiveError, ArchiveLimits, ArchiveReader, extract_members, validate_members
from .bytes import read_bytes


def list_files(path: str, store: FileStore | None = None, *,
               reader: ArchiveReader, limits: ArchiveLimits = ArchiveLimits()) -> list[str]:
    data = read_bytes(path, store)
    if len(data) > limits.packed_bytes:
        raise ArchiveError("archive.size_limit")
    with reader.open(data) as contents:
        members = contents.members()
        validate_members(members, limits)
        return [member.name for member in members]


def extract_to_memory(path: str, store: FileStore | None = None, *,
                      reader: ArchiveReader, limits: ArchiveLimits = ArchiveLimits()) -> dict[str, bytes]:
    return extract_members(read_bytes(path, store), select=tuple, limits=limits, rar_reader=reader)
