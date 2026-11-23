"""Requests and source evidence for the CBR file catalog."""

from dataclasses import dataclass, field
from typing import Mapping

from stratbox.core.network import RetryPolicy
from stratbox.shared.evidence import AcquiredSource
from stratbox.core.operations.source.original_definitions import OriginalDestination, StoredOriginal
from stratbox.core.operations.materials.archive_definitions import ArchiveMember
from stratbox.shared.material_collections import CollectionManifest


@dataclass(frozen=True, slots=True)
class CbrFileRegistryItem:
    source_id: str
    url: str
    title: str = ""
    expected_file_name: str | None = None
    series_id: str | None = None


@dataclass(frozen=True, slots=True)
class DiscoverFilesRequest:
    pass


@dataclass(frozen=True, slots=True)
class CollectFilesRequest:
    source_ids: tuple[str, ...]
    continue_on_error: bool = True
    try_case_variants: bool = True
    deadline_per_source_seconds: float = 60
    max_batch_bytes: int = 256 * 1024 * 1024
    retry: RetryPolicy = RetryPolicy()


@dataclass(frozen=True, slots=True)
class CollectedFile:
    source_id: str
    file_name: str
    source: AcquiredSource


@dataclass(frozen=True, slots=True)
class StoredCollectedFile:
    source_id: str
    file_name: str
    source: StoredOriginal


@dataclass(frozen=True, slots=True)
class CollectToStoreRequest:
    selection: CollectFilesRequest
    destinations: Mapping[str, OriginalDestination]


@dataclass(frozen=True, slots=True)
class CollectFailure:
    source_id: str
    code: str


@dataclass(frozen=True, slots=True)
class Collection:
    selected: tuple[str, ...]
    attempted: tuple[str, ...]
    completed: tuple[CollectedFile | StoredCollectedFile, ...]
    failed: tuple[CollectFailure, ...]
    not_attempted: tuple[str, ...]
    interrupted: CollectFailure | None = None
    stop_reason: str | None = None
    unresolved: StoredCollectedFile | None = None
    files: tuple[CollectedFile, ...] = field(init=False)
    stored_files: tuple[StoredCollectedFile, ...] = field(init=False)
    manifest: CollectionManifest = field(init=False)
    archive_members: tuple[ArchiveMember, ...] = field(init=False)

    def __post_init__(self):
        from .manifests import collection_manifest
        object.__setattr__(self, "files", tuple(item for item in self.completed if isinstance(item, CollectedFile)))
        object.__setattr__(self, "stored_files", tuple(item for item in self.completed if isinstance(item, StoredCollectedFile)))
        manifest = collection_manifest(self)
        object.__setattr__(self, "manifest", manifest)
        object.__setattr__(self, "archive_members", tuple(ArchiveMember(member.name,
            item.source.payload if isinstance(item, CollectedFile) else item.source.material)
            for item, member in zip(self.completed, manifest.members)))


@dataclass(frozen=True, slots=True)
class PrepareArchiveRequest:
    files: tuple[CollectedFile, ...]


@dataclass(frozen=True, slots=True)
class StoreArchiveRequest:
    files: tuple[StoredCollectedFile, ...]
    destination: OriginalDestination
