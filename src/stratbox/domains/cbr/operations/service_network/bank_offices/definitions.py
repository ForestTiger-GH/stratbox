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


PARSE = _registry_definition('cbr.offices.parse')

ACQUIRE = _registry_definition('cbr.offices.acquire')

CAPTURE = _registry_definition('cbr.offices.capture')

READ = _registry_definition('cbr.offices.read_representation')

COMPARE = _registry_definition('cbr.offices.compare')

SNAPSHOT = _registry_definition('cbr.offices.snapshot')

RESTORE = _registry_definition('cbr.offices.restore')
