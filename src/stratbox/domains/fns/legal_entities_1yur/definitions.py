"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import CompareReleaseRequest, ParsedRelease, ReadReleaseRequest, ReleaseLink
from stratbox.core.execution.contracts import OperationDefinition

DATASET = "fns.1yur"

METHOD = "fns-1yur-part-i-1"

_HTTP = frozenset({"http"})

@dataclass(frozen=True, slots=True)
class Discover1YurRequest:
    year: int
    index: SourcePayload | None = None
    index_url: str | None = None

@dataclass(frozen=True, slots=True)
class ReleaseIndex:
    releases: tuple[ReleaseLink, ...]
    missing_assets: tuple[date, ...]

@dataclass(frozen=True, slots=True)
class Parse1YurRequest:
    payload: SourcePayload
    as_of: date

DISCOVER = OperationDefinition(
    f"{DATASET}.discover", 1, "fns-1yur-index-1", Discover1YurRequest, ReleaseIndex,
    optional_capabilities=frozenset({"http"}),
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire", 1, METHOD, ReleaseLink, AcquiredSource, _HTTP
)

_RAR = frozenset({"archive_decoder"})

PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, Parse1YurRequest, ParsedRelease, optional_capabilities=_RAR,
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 1, METHOD, ReleaseLink, ParsedRelease, _HTTP, optional_capabilities=_RAR,
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "fns-1yur-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare", 2, "fns-1yur-compare-1", CompareReleaseRequest, Comparison
)

