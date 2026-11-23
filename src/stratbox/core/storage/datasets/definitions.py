"""Declarative logical dataset operation contracts, without executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from dataclasses import dataclass

from stratbox.core.limits import ExecutionBudget
from stratbox.core.runtime.capabilities import ProviderSelection
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot, SnapshotReference
from stratbox.shared.data.query import TableQuery, TablePreview
from stratbox.shared.identity import ByteIdentity
from .ports import DatasetWriteResult


@dataclass(frozen=True, slots=True)
class ReadSnapshotRequest:
    reference: SnapshotReference
    components: tuple[str, ...] | None = None
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class WriteSnapshotRequest:
    snapshot: DatasetSnapshot | DatasetAssembly
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class ListVersionsRequest:
    dataset_id: str
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class DatasetVersions:
    dataset_id: str
    references: tuple[SnapshotReference, ...]


@dataclass(frozen=True, slots=True)
class QuerySnapshotRequest:
    snapshot: DatasetSnapshot
    query: TableQuery
    expected_identity: ByteIdentity | None = None


QUERY = _registry_definition('dataset.query_snapshot')


READ = _registry_definition('dataset.read_snapshot')

WRITE = _registry_definition('dataset.write_snapshot')

LIST = _registry_definition('dataset.list_versions')
