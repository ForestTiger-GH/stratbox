"""Aggregate system-owned operation contracts independently of domains."""

from .execution.registry import OperationCatalog, merge_catalogs
from .execution.registration import REGISTRATION as EXECUTION
from .notifications.registration import REGISTRATION as NOTIFICATIONS


def system_catalog() -> OperationCatalog:
    return merge_catalogs(
        OperationCatalog(EXECUTION.operations),
        OperationCatalog(NOTIFICATIONS.operations),
    )
