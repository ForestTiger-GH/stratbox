"""Aggregate system-owned operation contracts independently of domains."""

from stratbox.core.execution.catalog import OperationCatalog, merge_catalogs
from stratbox.core.operations.source.registration import REGISTRATION as EXECUTION
from stratbox.core.notifications.registration import REGISTRATION as NOTIFICATIONS


def system_catalog() -> OperationCatalog:
    return merge_catalogs(
        OperationCatalog(EXECUTION.operations),
        OperationCatalog(NOTIFICATIONS.operations),
    )
