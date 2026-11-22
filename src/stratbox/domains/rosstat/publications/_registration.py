"""Registered owner of publisher-distribution operations."""

from stratbox.core.execution.catalog import OperationRef, OperationRegistration

_BASE = "stratbox.domains.rosstat.publications.operations"

REGISTRATION = OperationRegistration(
    owner_id="rosstat.publications",
    operations=(
        OperationRef("rosstat.publications.discover", 1, 'stratbox.domains.rosstat.publications.definitions:DISCOVER', _BASE + ":discover"),
        OperationRef("rosstat.publications.acquire", 1, 'stratbox.domains.rosstat.publications.definitions:ACQUIRE', _BASE + ":acquire"),
        OperationRef("rosstat.publications.acquire_to_store", 1, 'stratbox.domains.rosstat.publications.definitions:ACQUIRE_TO_STORE', _BASE + ":acquire_to_store"),
    ),
)
