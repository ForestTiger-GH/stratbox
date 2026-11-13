"""Requests and source evidence for the CBR file catalog."""

from dataclasses import dataclass
from typing import Mapping

from stratbox.base.net import RetryPolicy
from stratbox.data import AcquiredSource
from stratbox.execution.originals import OriginalDestination, StoredOriginal


@dataclass(frozen=True, slots=True)
class CbrFileRegistryItem:
    source_id: str
    url: str
    title: str = ""
    expected_file_name: str | None = None


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


@dataclass(frozen=True, slots=True)
class PrepareArchiveRequest:
    files: tuple[CollectedFile, ...]


@dataclass(frozen=True, slots=True)
class StoreArchiveRequest:
    files: tuple[StoredCollectedFile, ...]
    destination: OriginalDestination
