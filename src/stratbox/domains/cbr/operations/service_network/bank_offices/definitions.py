"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition


from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
)
from stratbox.domains.cbr.tables.service_network.bank_offices.contracts import AcquireOfficesRequest, AcquiredOffices, ParseOfficesRequest, ReadOfficesRequest, SnapshotOfficesRequest
from stratbox.shared.data.snapshots import DatasetSnapshot

from stratbox.shared.data.processing import DataContract, DataRole

DATASET = "cbr.offices"

METHOD = "cbr-offices-html-1"


PARSE = _registry_definition('cbr.offices.parse', 1)

ACQUIRE = _registry_definition('cbr.offices.acquire', 2)

CAPTURE = _registry_definition('cbr.offices.capture', 2)

READ = _registry_definition('cbr.offices.read_representation', 2)

COMPARE = _registry_definition('cbr.offices.compare', 2)

SNAPSHOT = _registry_definition('cbr.offices.snapshot', 1)

RESTORE = _registry_definition('cbr.offices.restore', 1)
