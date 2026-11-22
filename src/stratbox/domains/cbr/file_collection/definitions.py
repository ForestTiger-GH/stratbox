"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import CollectFilesRequest, CollectToStoreRequest, Collection, DiscoverFilesRequest, PrepareArchiveRequest, StoreArchiveRequest

DISCOVER = OperationDefinition("cbr.file_collector.discover", 1, "cbr-file-catalog-1", DiscoverFilesRequest, tuple)

COLLECT = OperationDefinition("cbr.file_collector.collect_raw", 2, "cbr-file-acquisition-1",
                              CollectFilesRequest, Collection, frozenset({"http"}), partial_allowed=True)

ARCHIVE = OperationDefinition("cbr.file_collector.prepare_archive", 1, "cbr-file-zip-1",
                              PrepareArchiveRequest, Representation)

COLLECT_TO_STORE = OperationDefinition(
    "cbr.file_collector.collect_to_store", 1, "cbr-file-stream-1", CollectToStoreRequest, Collection,
    frozenset({"http", "output_filestore"}), frozenset({"storage.write"}), partial_allowed=True,
    limits=ExecutionBudget(temporary_bytes=256 * 1024 * 1024, output_bytes=256 * 1024 * 1024),
)

ARCHIVE_TO_STORE = OperationDefinition(
    "cbr.file_collector.archive_to_store", 1, "cbr-file-stream-zip-1", StoreArchiveRequest, PathArchiveReceipt,
    frozenset({"filestore", "output_filestore"}), frozenset({"storage.write"}),
    limits=ExecutionBudget(input_bytes=256 * 1024 * 1024, output_bytes=257 * 1024 * 1024,
                           temporary_bytes=257 * 1024 * 1024),
)

