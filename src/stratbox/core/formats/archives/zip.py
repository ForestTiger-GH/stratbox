"""ZIP format commands over FileStore and in-memory data."""

from stratbox.core.storage.filestore import FileStore
from stratbox.core.runtime.providers import default_filestore
from stratbox.core.limits import BudgetMeter

from stratbox.core.formats.archives.members import ArchiveError, ArchiveLimits, extract_members, open_zip, zip_bytes
from stratbox.core.storage.bytes import read_bounded_bytes, write_bytes


def list_files(path: str, store: FileStore | None = None, *, limits: ArchiveLimits = ArchiveLimits(),
               budget: BudgetMeter | None = None) -> list[str]:
    with open_zip(_read(path, store, limits, budget), limits, budget=budget) as archive:
        return archive.namelist()


def extract_to_memory(path: str, store: FileStore | None = None, *,
                      limits: ArchiveLimits = ArchiveLimits(),
                      budget: BudgetMeter | None = None) -> dict[str, bytes]:
    return extract_members(_read(path, store, limits, budget), select=tuple, limits=limits, budget=budget)


def _read(path, store, limits, budget):
    try:
        return read_bounded_bytes(path, store=default_filestore(store),
                                  limit=limits.packed_bytes, budget=budget)
    except ValueError:
        raise ArchiveError("archive.size_limit") from None


def write_zip_from_memory(path: str, files: dict[str, bytes], store: FileStore | None = None, *,
                          limits: ArchiveLimits = ArchiveLimits()):
    return write_bytes(path, zip_bytes(files, limits=limits), store)
