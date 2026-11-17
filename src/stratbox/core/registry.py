"""Aggregate core-owned operation contracts independently of domains."""

from stratbox.core.execution.catalog import OperationCatalog, merge_catalogs
from stratbox.core.operations.source.registration import REGISTRATION as SOURCE
from stratbox.core.notifications.registration import REGISTRATION as NOTIFICATIONS


def core_catalog() -> OperationCatalog:
    return merge_catalogs(
        OperationCatalog(SOURCE.operations),
        OperationCatalog(NOTIFICATIONS.operations),
    )
