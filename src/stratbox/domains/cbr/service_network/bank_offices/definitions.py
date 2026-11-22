"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
)
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import AcquireOfficesRequest, AcquiredOffices, ParseOfficesRequest

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

DATASET = "cbr.offices"

METHOD = "cbr-offices-html-1"

_HTTP = frozenset({"http"})

PARSE = OperationDefinition(
    f"{DATASET}.parse",
    1,
    METHOD,
    ParseOfficesRequest,
    ParsedRelease,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract a source-local release while preserving source meaning and evidence.",
        inputs=(
            InputPort(
                "source",
                DataContract("cbr.offices.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.offices",)),
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("cbr.offices.release", 1, DataRole.EXTRACTS)
            ),
            OutputPort(
                "representation",
                DataContract(
                    "cbr.offices.extract_representation", 1, DataRole.EXTRACTS
                ),
                path="representation",
            ),
        ),
        parameters=("captured_on", "official_as_of"),
    ),
)

ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    2,
    "cbr-offices-http-2",
    AcquireOfficesRequest,
    AcquiredOffices,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire the selected source material with byte and acquisition evidence.",
        outputs=(
            OutputPort(
                "source",
                DataContract("cbr.offices.original", 1, DataRole.ORIGINALS),
                path="source.payload",
                qualifications=frozenset(("source.cbr.offices",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="source.payload",
            ),
        ),
        parameters=("capture_zone", "baseline"),
    ),
)

CAPTURE = OperationDefinition(
    f"{DATASET}.capture",
    2,
    METHOD,
    AcquireOfficesRequest,
    ParsedRelease,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.EXTRACT),
        summary="Acquire and extract a release in one invocation.",
        outputs=(
            OutputPort(
                "release", DataContract("cbr.offices.release", 1, DataRole.EXTRACTS)
            ),
            OutputPort(
                "representation",
                DataContract(
                    "cbr.offices.extract_representation", 1, DataRole.EXTRACTS
                ),
                path="representation",
            ),
        ),
        parameters=("capture_zone", "baseline"),
        composition=True,
    ),
)

READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
    processing=OperationSemantics(
        stages=(ProcessingStage.READ_EXTRACT,),
        summary="Validate a retained extract representation and rebuild its release envelope.",
        inputs=(
            InputPort(
                "representation",
                DataContract(
                    "cbr.offices.extract_representation", 1, DataRole.EXTRACTS
                ),
                path="payload",
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("cbr.offices.release", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("as_of",),
    ),
)

COMPARE = OperationDefinition(
    f"{DATASET}.compare",
    2,
    "cbr-offices-compare-1",
    CompareReleaseRequest,
    Comparison,
    processing=OperationSemantics(
        stages=(ProcessingStage.INSPECT, ProcessingStage.COMPARE),
        summary="Compare compatible release layers and retain indeterminate assessments.",
        inputs=(
            InputPort(
                "candidate",
                DataContract("cbr.offices.release", 1, DataRole.EXTRACTS),
                path="candidate",
            ),
            InputPort(
                "baseline",
                DataContract("cbr.offices.release", 1, DataRole.EXTRACTS),
                path="baseline",
                required=False,
            ),
        ),
        outputs=(
            OutputPort("comparison", DataContract("cbr.offices.comparison", 1, None)),
        ),
        parameters=("baseline_state",),
    ),
)
