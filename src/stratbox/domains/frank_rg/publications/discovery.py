"""Bounded directory discovery through a caller-selected FileStore."""
from __future__ import annotations

from stratbox.core.storage.filestore.paths import child_path
from stratbox.core.storage.filestore.types import DIRECTORY_GUARD_NAME
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from .contracts import DiscoveryRequest, FileEntry, SourceIndex

_MAX_ENTRIES = 100_000


def index_identity(request: DiscoveryRequest, entries: tuple[FileEntry, ...]) -> ByteIdentity:
    """Identify the observation; this is deliberately not a digest of file bytes."""
    return ByteIdentity.of(canonical_manifest_bytes({
        "schema": 1, "directory": request.directory,
        "recursive": request.recursive, "families": list(request.family_ids),
        "entries": [{"path": item.path, "filename": item.filename,
                     "size": item.size_bytes,
                     "mtime": float(item.mtime).hex() if item.mtime is not None else None}
                    for item in entries],
    }))


def validate_index(index: SourceIndex) -> None:
    if not isinstance(index, SourceIndex) or not isinstance(index.entries, tuple):
        raise ValueError("frg.index.invalid")
    request = DiscoveryRequest(index.directory, index.recursive, index.family_ids)
    _validate_request(request)
    if (len(index.entries) > _MAX_ENTRIES or any(not isinstance(x, FileEntry) for x in index.entries)
            or len({x.path for x in index.entries}) != len(index.entries)
            or tuple(sorted(index.entries, key=lambda x: x.path)) != index.entries
            or index.identity != index_identity(request, index.entries)
            or index.inventory_coverage != "unknown"):
        raise ValueError("frg.index.invalid")


def _validate_request(request: DiscoveryRequest) -> None:
    if (not isinstance(request.directory, str) or not request.directory or "\x00" in request.directory
            or type(request.recursive) is not bool or not isinstance(request.family_ids, tuple)
            or any(not isinstance(x, str) or not x for x in request.family_ids)
            or len(set(request.family_ids)) != len(request.family_ids)):
        raise ValueError("frg.discovery.request_invalid")


def discover_directory(request: DiscoveryRequest, store, invocation=None) -> SourceIndex:
    """Enumerate regular files without opening workbooks or applying effects."""
    _validate_request(request)
    if not store.is_dir(request.directory):
        raise ValueError("frg.discovery.directory_unavailable")
    root = store.stat(request.directory)
    if root.is_symlink or not root.is_dir:
        raise ValueError("frg.discovery.directory_invalid")
    entries: list[FileEntry] = []
    visited: set[str] = set()
    count = 0
    pending = [request.directory]
    while pending:
        directory = pending.pop()
        if directory in visited:
            raise ValueError("frg.discovery.directory_cycle")
        visited.add(directory)
        listing = getattr(store, "iter_names", store.listdir)
        names_seen = set()
        children = []
        for name in listing(directory):
            if name == DIRECTORY_GUARD_NAME:
                continue
            if invocation is not None:
                invocation.check_cancelled()
                invocation.budget.charge("objects", 1)
            count += 1
            if count > _MAX_ENTRIES:
                raise ValueError("frg.discovery.entry_limit")
            if name in names_seen:
                raise ValueError("frg.discovery.duplicate_entry")
            names_seen.add(name)
            path = child_path(directory, name)
            info = store.stat(path)
            if info.is_symlink:
                raise ValueError("frg.discovery.symbolic_entry")
            if info.is_file:
                entries.append(FileEntry(path, name, info.size, info.mtime))
            elif info.is_dir and request.recursive:
                children.append(path)
        pending.extend(sorted(children, reverse=True))
    ordered = tuple(sorted(entries, key=lambda x: x.path))
    return SourceIndex(request.directory, ordered, index_identity(request, ordered),
                       request.family_ids, request.recursive)
