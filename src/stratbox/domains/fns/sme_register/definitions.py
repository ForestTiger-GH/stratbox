"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import CompareReleaseRequest, ParsedRelease, ReadReleaseRequest
from stratbox.core.execution.contracts import OperationDefinition

DATASET = "fns.sme"

METHOD = "fns-sme-regional-json-1"

_HTTP = frozenset({"http"})

@dataclass(frozen=True, slots=True)
class DiscoverSmeRequest:
    index: SourcePayload | None = None

@dataclass(frozen=True, slots=True)
class AcquireSmeRequest:
    as_of: date

@dataclass(frozen=True, slots=True)
class ParseSmeRequest:
    payload: SourcePayload
    as_of: date

DISCOVER = OperationDefinition(
    f"{DATASET}.discover", 1, "fns-sme-index-1", DiscoverSmeRequest, tuple,
    optional_capabilities=frozenset({"http"}),
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    1,
    "fns-sme-regional-post-1",
    AcquireSmeRequest,
    AcquiredSource,
    _HTTP,
)

PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, ParseSmeRequest, ParsedRelease
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 1, METHOD, AcquireSmeRequest, ParsedRelease, _HTTP
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "fns-sme-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare", 2, "fns-sme-compare-1", CompareReleaseRequest, Comparison
)

