"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition


from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReleaseLink,
)

from stratbox.shared.data.processing import DataContract, DataRole

from stratbox.domains.cbr.tables.service_network.territorial_offices.contracts import DiscoverOfficesRegRequest, ParseOfficesRegRequest, OfficesRegCandidates, ReadOfficesRegRequest, SnapshotOfficesRegRequest

DATASET = "cbr.offices_reg"

METHOD = "cbr-offices-reg-xlsx-4"


DISCOVER = _registry_definition('cbr.offices_reg.discover')

ACQUIRE = _registry_definition('cbr.offices_reg.acquire')

PARSE = _registry_definition('cbr.offices_reg.parse')

CAPTURE = _registry_definition('cbr.offices_reg.capture')

READ = _registry_definition('cbr.offices_reg.read_representation')

COMPARE = _registry_definition('cbr.offices_reg.compare')

SNAPSHOT = _registry_definition('cbr.offices_reg.snapshot')

RESTORE = _registry_definition('cbr.offices_reg.restore')
