"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import AcquireRosstatRequest, AcquireRosstatToStoreRequest, AcquiredRosstatAsset, DiscoverRosstatRequest, RosstatPublicationIndex, StoredRosstatAsset

_HTTP = frozenset({"http"})

_OUTPUT = frozenset({"output_filestore"})

_WRITE = frozenset({"storage.write"})

_LIMIT = 256 * 1024 * 1024

DISCOVER = OperationDefinition(
    "rosstat.publications.discover", 1, "rosstat-source-links-1",
    DiscoverRosstatRequest, RosstatPublicationIndex, optional_capabilities=_HTTP,
)

ACQUIRE = OperationDefinition(
    "rosstat.publications.acquire", 1, "rosstat-original-envelope-1",
    AcquireRosstatRequest, AcquiredRosstatAsset, _HTTP,
    limits=ExecutionBudget(input_bytes=_LIMIT, output_bytes=_LIMIT, temporary_bytes=_LIMIT),
)

ACQUIRE_TO_STORE = OperationDefinition(
    "rosstat.publications.acquire_to_store", 1, "rosstat-original-stream-1",
    AcquireRosstatToStoreRequest, StoredRosstatAsset, _HTTP | _OUTPUT, _WRITE,
    optional_capabilities=frozenset({"filestore"}),
    limits=ExecutionBudget(input_bytes=_LIMIT, output_bytes=_LIMIT, temporary_bytes=_LIMIT),
)

