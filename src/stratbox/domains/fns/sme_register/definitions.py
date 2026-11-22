"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
)
from stratbox.core.execution.contracts import OperationDefinition

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

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
    f"{DATASET}.discover",
    1,
    "fns-sme-index-1",
    DiscoverSmeRequest,
    tuple,
    optional_capabilities=frozenset({"http"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Discover source issues with source-specific identity and coverage.",
        inputs=(
            InputPort(
                "index",
                DataContract("fns.sme.index_material", 1, DataRole.ORIGINALS),
                path="index",
                required=False,
            ),
        ),
        outputs=(OutputPort("releases", DataContract("fns.sme.index", 1, None)),),
    ),
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    1,
    "fns-sme-regional-post-1",
    AcquireSmeRequest,
    AcquiredSource,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire the selected source material with byte and acquisition evidence.",
        outputs=(
            OutputPort(
                "source",
                DataContract("fns.sme.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.fns.sme",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="payload",
            ),
        ),
        parameters=("as_of",),
    ),
)

PARSE = OperationDefinition(
    f"{DATASET}.parse",
    1,
    METHOD,
    ParseSmeRequest,
    ParsedRelease,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract a source-local release while preserving source meaning and evidence.",
        inputs=(
            InputPort(
                "source",
                DataContract("fns.sme.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.fns.sme",)),
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("fns.sme.release", 1, DataRole.EXTRACTS)
            ),
            OutputPort(
                "representation",
                DataContract("fns.sme.extract_representation", 1, DataRole.EXTRACTS),
                path="representation",
            ),
        ),
        parameters=("as_of",),
    ),
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture",
    1,
    METHOD,
    AcquireSmeRequest,
    ParsedRelease,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.EXTRACT),
        summary="Acquire and extract a release in one invocation.",
        outputs=(
            OutputPort(
                "release", DataContract("fns.sme.release", 1, DataRole.EXTRACTS)
            ),
            OutputPort(
                "representation",
                DataContract("fns.sme.extract_representation", 1, DataRole.EXTRACTS),
                path="representation",
            ),
        ),
        parameters=("as_of",),
        composition=True,
    ),
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "fns-sme-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
    processing=OperationSemantics(
        stages=(ProcessingStage.READ_EXTRACT,),
        summary="Validate a retained extract representation and rebuild its release envelope.",
        inputs=(
            InputPort(
                "representation",
                DataContract("fns.sme.extract_representation", 1, DataRole.EXTRACTS),
                path="payload",
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("fns.sme.release", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("as_of",),
    ),
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare",
    2,
    "fns-sme-compare-1",
    CompareReleaseRequest,
    Comparison,
    processing=OperationSemantics(
        stages=(ProcessingStage.INSPECT, ProcessingStage.COMPARE),
        summary="Compare compatible release layers and retain indeterminate assessments.",
        inputs=(
            InputPort(
                "candidate",
                DataContract("fns.sme.release", 1, DataRole.EXTRACTS),
                path="candidate",
            ),
            InputPort(
                "baseline",
                DataContract("fns.sme.release", 1, DataRole.EXTRACTS),
                path="baseline",
                required=False,
            ),
        ),
        outputs=(
            OutputPort("comparison", DataContract("fns.sme.comparison", 1, None)),
        ),
        parameters=("baseline_state",),
    ),
)
