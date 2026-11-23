"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.core.limits import ExecutionBudget
from ..publications.contracts import (
    AcquireRosstatRequest,
    AcquireRosstatToStoreRequest,
    AcquiredRosstatAsset,
    DiscoverRosstatRequest,
    RosstatPublicationIndex,
    StoredRosstatAsset,
)

from stratbox.shared.data.processing import DataContract, DataRole

_HTTP = frozenset({"http"})

_OUTPUT = frozenset({"output_filestore"})

_WRITE = frozenset({"storage.write"})

_LIMIT = 256 * 1024 * 1024

DISCOVER = _registry_definition('rosstat.publications.discover')

ACQUIRE = _registry_definition('rosstat.publications.acquire')

ACQUIRE_TO_STORE = _registry_definition('rosstat.publications.acquire_to_store')
