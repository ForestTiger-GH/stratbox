"""Lazy registration of storage-independent logical dataset operations."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(owner_id="core.datasets", operations=(
    OperationRef("dataset.query_snapshot", 1, "stratbox.core.storage.datasets.definitions:QUERY", "stratbox.core.storage.datasets.operations:query_snapshot"),
    OperationRef("dataset.read_snapshot", 1, "stratbox.core.storage.datasets.definitions:READ", "stratbox.core.storage.datasets.operations:read_snapshot"),
    OperationRef("dataset.write_snapshot", 1, "stratbox.core.storage.datasets.definitions:WRITE", "stratbox.core.storage.datasets.operations:write_snapshot"),
    OperationRef("dataset.list_versions", 1, "stratbox.core.storage.datasets.definitions:LIST", "stratbox.core.storage.datasets.operations:list_versions"),
))
