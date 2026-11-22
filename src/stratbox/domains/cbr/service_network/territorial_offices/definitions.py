"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
    ReleaseLink,
)
from stratbox.core.execution.contracts import OperationDefinition

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

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
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Discover source issues with source-specific identity and coverage.",
        inputs=(
            InputPort(
                "index",
                DataContract("cbr.offices_reg.index_material", 1, DataRole.ORIGINALS),
                path="index",
                required=False,
            ),
        ),
        outputs=(
            OutputPort("releases", DataContract("cbr.offices_reg.index", 1, None)),
        ),
    ),
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    1,
    METHOD,
    ReleaseLink,
    AcquiredSource,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire the selected source material with byte and acquisition evidence.",
        outputs=(
            OutputPort(
                "source",
                DataContract("cbr.offices_reg.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.offices_reg",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="payload",
            ),
        ),
        parameters=("as_of", "url"),
    ),
)

PARSE = OperationDefinition(
    f"{DATASET}.parse",
    3,
    METHOD,
    ParseOfficesRegRequest,
    (ParsedRelease, OfficesRegCandidates),
    partial_allowed=True,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract a source-local release while preserving source meaning and evidence.",
        inputs=(
            InputPort(
                "source",
                DataContract("cbr.offices_reg.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.offices_reg",)),
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("cbr.offices_reg.release", 1, DataRole.EXTRACTS)
            ),
            OutputPort(
                "representation",
                DataContract(
                    "cbr.offices_reg.extract_representation", 1, DataRole.EXTRACTS
                ),
                path="representation",
            ),
        ),
        parameters=("as_of", "sheet", "national_row", "last_row"),
    ),
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture",
    3,
    METHOD,
    ReleaseLink,
    (ParsedRelease, OfficesRegCandidates),
    _HTTP,
    partial_allowed=True,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.EXTRACT),
        summary="Acquire and extract a release in one invocation.",
        outputs=(
            OutputPort(
                "release", DataContract("cbr.offices_reg.release", 1, DataRole.EXTRACTS)
            ),
            OutputPort(
                "representation",
                DataContract(
                    "cbr.offices_reg.extract_representation", 1, DataRole.EXTRACTS
                ),
                path="representation",
            ),
        ),
        parameters=("as_of", "url"),
        composition=True,
    ),
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-reg-csv-2",
    ReadReleaseRequest,
    ParsedRelease,
    processing=OperationSemantics(
        stages=(ProcessingStage.READ_EXTRACT,),
        summary="Validate a retained extract representation and rebuild its release envelope.",
        inputs=(
            InputPort(
                "representation",
                DataContract(
                    "cbr.offices_reg.extract_representation", 1, DataRole.EXTRACTS
                ),
                path="payload",
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("cbr.offices_reg.release", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("as_of",),
    ),
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare",
    2,
    "cbr-offices-reg-compare-2",
    CompareReleaseRequest,
    Comparison,
    processing=OperationSemantics(
        stages=(ProcessingStage.INSPECT, ProcessingStage.COMPARE),
        summary="Compare compatible release layers and retain indeterminate assessments.",
        inputs=(
            InputPort(
                "candidate",
                DataContract("cbr.offices_reg.release", 1, DataRole.EXTRACTS),
                path="candidate",
            ),
            InputPort(
                "baseline",
                DataContract("cbr.offices_reg.release", 1, DataRole.EXTRACTS),
                path="baseline",
                required=False,
            ),
        ),
        outputs=(
            OutputPort(
                "comparison", DataContract("cbr.offices_reg.comparison", 1, None)
            ),
        ),
        parameters=("baseline_state",),
    ),
)
