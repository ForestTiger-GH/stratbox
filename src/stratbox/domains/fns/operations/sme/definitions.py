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
    ProcessingFunction,
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
        stages=(ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE, ProcessingStage.VIEW, ProcessingStage.RENDER),
        composition=True,
        summary="Compose the explicit reviewed regional CSV product; complete source flakes use the independent extract route.",
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
                "release", DataContract("fns.sme.regional_release", 1, DataRole.PRODUCTS)
            ),
            OutputPort(
                "representation",
                DataContract("fns.sme.regional_csv", 1, DataRole.PRODUCTS),
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
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE, ProcessingStage.VIEW, ProcessingStage.RENDER),
        summary="Acquire and compose the reviewed regional CSV subset; capture_full returns every processing boundary.",
        outputs=(
            OutputPort(
                "release", DataContract("fns.sme.regional_release", 1, DataRole.PRODUCTS)
            ),
            OutputPort(
                "representation",
                DataContract("fns.sme.regional_csv", 1, DataRole.PRODUCTS),
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
        stages=(), function=ProcessingFunction.REPLAY,
        summary="Import an explicitly selected regional CSV product; original-wide source coverage remains qualified.",
        inputs=(
            InputPort(
                "representation",
                DataContract("fns.sme.regional_csv", 1, DataRole.PRODUCTS),
                path="payload",
            ),
        ),
        outputs=(
            OutputPort(
                "release", DataContract("fns.sme.regional_release", 1, DataRole.PRODUCTS)
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
        summary="Compare selected regional product releases with their historical qualifiers intact.",
        inputs=(
            InputPort(
                "candidate",
                DataContract("fns.sme.regional_release", 1, DataRole.PRODUCTS),
                path="candidate",
            ),
            InputPort(
                "baseline",
                DataContract("fns.sme.regional_release", 1, DataRole.PRODUCTS),
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


from ...tables.contracts import JsonFlake
from ..pipeline_definitions import definitions as _pipeline_definitions

globals().update(_pipeline_definitions(DATASET, JsonFlake))
