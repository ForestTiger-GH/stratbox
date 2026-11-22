"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import CompareReleaseRequest, ParsedRelease, ReadReleaseRequest, ReleaseLink
from stratbox.core.execution.contracts import OperationDefinition

DATASET = "cbr.offices_reg"

METHOD = "cbr-offices-reg-xlsx-4"

_HTTP = frozenset({"http"})

@dataclass(frozen=True, slots=True)
class DiscoverOfficesRegRequest:
    index: SourcePayload | None = None

@dataclass(frozen=True, slots=True)
class ParseOfficesRegRequest:
    payload: SourcePayload
    as_of: date
    sheet: str | None = None
    national_row: int | None = None
    last_row: int | None = None

@dataclass(frozen=True, slots=True)
class OfficesRegCandidates:
    source_identity: ByteIdentity
    blocks: tuple[tuple[str, int, int], ...]

DISCOVER = OperationDefinition(
    f"{DATASET}.discover",
    1,
    "cbr-offices-reg-index-1",
    DiscoverOfficesRegRequest,
    tuple,
    optional_capabilities=frozenset({"http"}),
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire", 1, METHOD, ReleaseLink, AcquiredSource, _HTTP
)

PARSE = OperationDefinition(
    f"{DATASET}.parse", 3, METHOD, ParseOfficesRegRequest,
    (ParsedRelease, OfficesRegCandidates), partial_allowed=True,
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 3, METHOD, ReleaseLink,
    (ParsedRelease, OfficesRegCandidates), _HTTP, partial_allowed=True,
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-reg-csv-2",
    ReadReleaseRequest,
    ParsedRelease,
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare",
    2,
    "cbr-offices-reg-compare-2",
    CompareReleaseRequest,
    Comparison,
)

