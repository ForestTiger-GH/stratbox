"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import CompareReleaseRequest, ParsedRelease, ReadReleaseRequest
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import AcquireOfficesRequest, AcquiredOffices, ParseOfficesRequest

DATASET = "cbr.offices"

METHOD = "cbr-offices-html-1"

_HTTP = frozenset({"http"})

PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, ParseOfficesRequest, ParsedRelease
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    2,
    "cbr-offices-http-2",
    AcquireOfficesRequest,
    AcquiredOffices,
    _HTTP,
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 2, METHOD, AcquireOfficesRequest, ParsedRelease, _HTTP
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare", 2, "cbr-offices-compare-1", CompareReleaseRequest, Comparison
)

