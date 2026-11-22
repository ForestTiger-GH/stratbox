"""Aggregate core-owned operation contracts independently of domains."""

from stratbox.core.execution.catalog import OperationCatalog
from stratbox.core.operations.source.registration import REGISTRATION as SOURCE
from stratbox.core.notifications.registration import REGISTRATION as NOTIFICATIONS
from stratbox.core.operations.materials.registration import REGISTRATION as MATERIALS
from stratbox.core.storage.datasets.registration import REGISTRATION as DATASETS


def core_catalog() -> OperationCatalog:
    return OperationCatalog.from_registrations(SOURCE, NOTIFICATIONS, MATERIALS, DATASETS)
