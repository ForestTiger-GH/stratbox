"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import (
    BuildFormDataRequest,
    FormData,
    FormKey,
    FormSnapshot,
    FormViews,
    ParseFormRequest,
    SelectFormSourcesRequest,
)

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)

SELECT = OperationDefinition(
    "cbr.forms.select_sources",
    1,
    "cbr-forms-source-selection-1",
    SelectFormSourcesRequest,
    tuple,
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Resolve reporting-form source keys.",
        outputs=(OutputPort("sources", DataContract("cbr.forms.sources", 1, None)),),
        parameters=("keys",),
    ),
)

ACQUIRE = OperationDefinition(
    "cbr.forms.acquire",
    1,
    "cbr-forms-source-1",
    FormKey,
    AcquiredSource,
    frozenset({"http"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire a selected official reporting form.",
        outputs=(
            OutputPort(
                "source",
                DataContract("cbr.forms.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.forms",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="payload",
            ),
        ),
        parameters=("code", "as_of"),
    ),
)

PARSE = OperationDefinition(
    "cbr.forms.parse",
    2,
    "cbr-forms-physical-layout-1",
    ParseFormRequest,
    FormSnapshot,
    optional_capabilities=frozenset({"archive_decoder"}),
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract the physical reporting-form layout without applying a business model.",
        inputs=(
            InputPort(
                "source",
                DataContract("cbr.forms.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.forms",)),
            ),
        ),
        outputs=(
            OutputPort(
                "snapshot", DataContract("cbr.forms.snapshot", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("key",),
    ),
)

BUILD = OperationDefinition(
    "cbr.forms.build_data",
    2,
    "cbr-forms-model-evaluation-1",
    BuildFormDataRequest,
    FormData,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE,),
        summary="Evaluate a reporting-form model over supplied snapshots.",
        inputs=(
            InputPort(
                "snapshots",
                DataContract("cbr.forms.snapshots", 1, DataRole.EXTRACTS),
                path="snapshots",
            ),
        ),
        outputs=(
            OutputPort("data", DataContract("cbr.forms.data", 1, DataRole.EXTRACTS)),
        ),
        parameters=("banks", "model"),
    ),
)

VIEWS = OperationDefinition(
    "cbr.forms.build_views",
    2,
    "cbr-forms-views-1",
    FormData,
    FormViews,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.VIEW,),
        summary="Construct reporting-form presentation views from evaluated data.",
        inputs=(
            InputPort("data", DataContract("cbr.forms.data", 1, DataRole.EXTRACTS)),
        ),
        outputs=(
            OutputPort("views", DataContract("cbr.forms.views", 1, DataRole.PRODUCTS)),
        ),
    ),
)

RENDER = OperationDefinition(
    "cbr.forms.render_workbook",
    2,
    "cbr-forms-xlsx-1",
    FormViews,
    Representation,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render supplied reporting-form views into workbook bytes.",
        inputs=(
            InputPort("views", DataContract("cbr.forms.views", 1, DataRole.PRODUCTS)),
        ),
        outputs=(
            OutputPort(
                "workbook", DataContract("cbr.forms.workbook", 1, DataRole.PRODUCTS)
            ),
        ),
    ),
)
