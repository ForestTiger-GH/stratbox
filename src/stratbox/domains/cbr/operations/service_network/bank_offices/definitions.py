"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.execution.semantics import technical_operation, ProcessingFunction

from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
)
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.domains.cbr.tables.service_network.bank_offices.contracts import AcquireOfficesRequest, AcquiredOffices, ParseOfficesRequest, ReadOfficesRequest, SnapshotOfficesRequest
from stratbox.shared.data.snapshots import DatasetSnapshot

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
                DataContract("material.payload", 1),
                path="payload",
                alternatives=(DataContract("cbr.offices.original", 1, DataRole.ORIGINALS),
                              DataContract("source.payload", 1, DataRole.ORIGINALS)),
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
    2,
    "cbr-offices-csv-explicit-period-2",
    ReadOfficesRequest,
    ParsedRelease,
    processing=OperationSemantics(
        stages=(ProcessingStage.READ_EXTRACT,),
        summary="Read CSV with explicit capture and observation dates; absent observation metadata remains literal-only.",
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
        parameters=("captured_on", "official_as_of", "period_basis"),
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

SNAPSHOT = technical_operation(OperationDefinition("cbr.offices.snapshot", 1, "cbr-offices-snapshot-1",
    SnapshotOfficesRequest, DatasetSnapshot,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("release", DataContract("cbr.offices.release", 1, DataRole.EXTRACTS), path="release"),),
        outputs=(OutputPort("snapshot", DataContract("dataset.snapshot", 1)),),
        parameters=("dataset_id", "version_id"),
        summary="Preserve observation and capture dates, literal cells, qualifications and complete source evidence.")), ProcessingFunction.ENCODE)

RESTORE = technical_operation(OperationDefinition("cbr.offices.restore", 1, "cbr-offices-replay-1",
    DatasetSnapshot, ParsedRelease,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("snapshot", DataContract("dataset.snapshot", 1)),),
        outputs=(OutputPort("release", DataContract("cbr.offices.release", 1, DataRole.EXTRACTS)),),
        summary="Restore a complete qualified office release without assigning a new capture or observation date.")), ProcessingFunction.REPLAY)
