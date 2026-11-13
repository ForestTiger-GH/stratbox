"""RAR format commands using an explicitly selected archive reader."""

from stratbox.base.filestore import FileStore, LocalFileStore
from stratbox.base.limits import BudgetMeter

from .archive_bytes import ArchiveError, ArchiveLimits, ArchiveReader, extract_members, validate_members
from .bytes import read_bounded_bytes


def list_files(path: str, store: FileStore | None = None, *,
               reader: ArchiveReader, limits: ArchiveLimits = ArchiveLimits(),
               budget: BudgetMeter | None = None) -> list[str]:
    data = _read(path, store, limits, budget)
    with reader.open(data) as contents:
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
        return read_bounded_bytes(path, store=store if store is not None else LocalFileStore(),
                                  limit=limits.packed_bytes, budget=budget)
    except ValueError:
        raise ArchiveError("archive.size_limit") from None
