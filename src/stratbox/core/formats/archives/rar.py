"""RAR format commands using an explicitly selected archive reader."""
from io import BytesIO

from stratbox.core.storage.filestore import FileStore
from stratbox.core.runtime.providers import default_filestore
from stratbox.core.limits import BudgetMeter

from stratbox.core.formats.archives.members import ArchiveError, ArchiveLimits, ArchiveReader, extract_members, validate_members
from stratbox.core.storage.bytes import read_bounded_bytes


def list_files(path: str, store: FileStore | None = None, *,
               reader: ArchiveReader, limits: ArchiveLimits = ArchiveLimits(),
               budget: BudgetMeter | None = None) -> list[str]:
    data = _read(path, store, limits, budget)
    with reader.open(BytesIO(data), limits=limits) as contents:
        members = contents.members()
        validate_members(members, limits)
        if budget is not None:
            budget.charge("objects", len(members))
        return [member.name for member in members]


def extract_to_memory(path: str, store: FileStore | None = None, *,
                      reader: ArchiveReader, limits: ArchiveLimits = ArchiveLimits(),
                      budget: BudgetMeter | None = None) -> dict[str, bytes]:
    return extract_members(_read(path, store, limits, budget), select=tuple, limits=limits,
                           rar_reader=reader, budget=budget)


def _read(path, store, limits, budget):
    try:
        return read_bounded_bytes(path, store=default_filestore(store),
                                  limit=limits.packed_bytes, budget=budget)
    except ValueError:
        raise ArchiveError("archive.size_limit") from None
