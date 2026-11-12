"""ZIP format commands over FileStore and in-memory data."""

from stratbox.base.filestore import FileStore

from .archive_bytes import ArchiveLimits, extract_members, open_zip, zip_bytes
from .bytes import read_bytes, write_bytes


def list_files(path: str, store: FileStore | None = None, *, limits: ArchiveLimits = ArchiveLimits()) -> list[str]:
    with open_zip(read_bytes(path, store), limits) as archive:
        return archive.namelist()


def extract_to_memory(path: str, store: FileStore | None = None, *,
                      limits: ArchiveLimits = ArchiveLimits()) -> dict[str, bytes]:
    return extract_members(read_bytes(path, store), select=tuple, limits=limits)


def write_zip_from_memory(path: str, files: dict[str, bytes], store: FileStore | None = None, *,
                          limits: ArchiveLimits = ArchiveLimits()):
    return write_bytes(path, zip_bytes(files, limits=limits), store)
