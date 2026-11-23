"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.representation import Representation
from stratbox.domains.cbr.publications.collection.contracts import CollectFilesRequest, CollectToStoreRequest, Collection, DiscoverFilesRequest, PrepareArchiveRequest, StoreArchiveRequest

from stratbox.shared.data.processing import DataContract, DataRole

DISCOVER = _registry_definition('cbr.file_collector.discover')

COLLECT = _registry_definition('cbr.file_collector.collect_raw')

ARCHIVE = _registry_definition('cbr.file_collector.prepare_archive')

COLLECT_TO_STORE = _registry_definition('cbr.file_collector.collect_to_store')

ARCHIVE_TO_STORE = _registry_definition('cbr.file_collector.archive_to_store')
