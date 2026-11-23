"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution.contracts import OperationDefinition
from ..publications.contracts import (
    AcquireRosstatRequest,
    AcquireRosstatToStoreRequest,
    AcquiredRosstatAsset,
    DiscoverRosstatRequest,
    RosstatPublicationIndex,
    StoredRosstatAsset,
)

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

_HTTP = frozenset({"http"})

_OUTPUT = frozenset({"output_filestore"})

_WRITE = frozenset({"storage.write"})

_LIMIT = 256 * 1024 * 1024

DISCOVER = OperationDefinition(
    "rosstat.publications.discover",
    1,
    "rosstat-source-links-1",
    DiscoverRosstatRequest,
    RosstatPublicationIndex,
    optional_capabilities=_HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Discover publisher assets with explicit index coverage and issue qualification.",
        inputs=(
            InputPort(
                "index",
                DataContract(
                    "rosstat.publications.index_material", 1, DataRole.ORIGINALS
                ),
                path="index",
                required=False,
            ),
        ),
        outputs=(
            OutputPort("index", DataContract("rosstat.publications.index", 1, None)),
        ),
        parameters=("series_id",),
    ),
)

ACQUIRE = OperationDefinition(
    "rosstat.publications.acquire",
    1,
    "rosstat-original-envelope-1",
    AcquireRosstatRequest,
    AcquiredRosstatAsset,
    _HTTP,
    limits=ExecutionBudget(
        input_bytes=_LIMIT, output_bytes=_LIMIT, temporary_bytes=_LIMIT
    ),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire a selected publisher asset and qualify its file envelope.",
        inputs=(
            InputPort(
                "asset",
                DataContract("rosstat.publications.asset", 1, None),
                path="asset",
            ),
        ),
        outputs=(
            OutputPort(
                "source",
                DataContract("rosstat.publications.original", 1, DataRole.ORIGINALS),
                path="source.payload",
                qualifications=frozenset(("source.rosstat.publications",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="source.payload",
            ),
        ),
        parameters=("max_bytes", "deadline_seconds", "retry"),
    ),
)

ACQUIRE_TO_STORE = OperationDefinition(
    "rosstat.publications.acquire_to_store",
    1,
    "rosstat-original-stream-1",
    AcquireRosstatToStoreRequest,
    StoredRosstatAsset,
    _HTTP | _OUTPUT,
    _WRITE,
    optional_capabilities=frozenset({"filestore"}),
    limits=ExecutionBudget(
        input_bytes=_LIMIT, output_bytes=_LIMIT, temporary_bytes=_LIMIT
    ),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE, ProcessingStage.PRESERVE),
        summary="Stream a publisher asset to storage and retain confirmed original evidence.",
        inputs=(
            InputPort(
                "asset",
                DataContract("rosstat.publications.asset", 1, None),
                path="asset",
            ),
        ),
        outputs=(
            OutputPort(
                "material",
                DataContract("source.material_reference", 1, DataRole.ORIGINALS),
                path="source.material",
                qualifications=frozenset(("storage.confirmed",)),
            ),
        ),
        parameters=(
            "destination",
            "max_bytes",
            "deadline_seconds",
            "retry",
            "baseline",
        ),
        composition=True,
    ),
)
