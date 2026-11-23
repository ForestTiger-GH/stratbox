"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition


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


DISCOVER = _registry_definition('cbr.offices_reg.discover', 1)

ACQUIRE = _registry_definition('cbr.offices_reg.acquire', 1)

PARSE = _registry_definition('cbr.offices_reg.parse', 3)

CAPTURE = _registry_definition('cbr.offices_reg.capture', 3)

READ = _registry_definition('cbr.offices_reg.read_representation', 2)

COMPARE = _registry_definition('cbr.offices_reg.compare', 2)

SNAPSHOT = _registry_definition('cbr.offices_reg.snapshot', 1)

RESTORE = _registry_definition('cbr.offices_reg.restore', 1)
