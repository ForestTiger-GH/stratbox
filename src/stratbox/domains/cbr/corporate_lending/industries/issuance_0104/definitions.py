"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.shared.evidence import AcquiredSource
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import (
    BuildIssuanceStreamRequest,
    CalculateIssuanceApkRequest,
    DiscoverIssuanceRequest,
    IssuanceSourceLink,
    IssuanceStreamResult,
    IssuanceWorkbookRequest,
    IssuanceWorkbookResult,
    IssuanceWorkbooksResult,
    ParseIssuanceRequest,
    ParsedIssuanceFile,
    PivotIssuanceRequest,
    RenderIssuanceIndustriesRequest,
)
from ..common.contracts import IndustryApkCalculationResult, IndustryPivotSetResult
from ..common.limits import TABLE_LIMITS as _TABLE_LIMITS

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

_DATASET = "cbr.industries.0104a"

DISCOVER = OperationDefinition(
    f"{_DATASET}.discover",
    1,
    "cbr-0104a-index-1",
    DiscoverIssuanceRequest,
    tuple,
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Discover the selected stock or flow publication series.",
        inputs=(
            InputPort(
                "index",
                DataContract(
                    "cbr.industries.0104a.index_material", 1, DataRole.ORIGINALS
                ),
                path="index",
                required=False,
            ),
        ),
        outputs=(
            OutputPort("sources", DataContract("cbr.industries.0104a.index", 1, None)),
        ),
        parameters=("date_from", "date_to"),
    ),
)

ACQUIRE = OperationDefinition(
    f"{_DATASET}.acquire",
    1,
    "cbr-0104a-source-1",
    IssuanceSourceLink,
    AcquiredSource,
    frozenset({"http"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire a selected industry workbook under its own publication contract.",
        inputs=(
            InputPort("source", DataContract("cbr.industries.0104a.source", 1, None)),
        ),
        outputs=(
            OutputPort(
                "source",
                DataContract("cbr.industries.0104a.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.industries.0104a",)),
            ),
            OutputPort(
                "payload",
                DataContract("source.payload", 1, DataRole.ORIGINALS),
                path="payload",
            ),
        ),
    ),
)

PARSE = OperationDefinition(
    f"{_DATASET}.parse",
    3,
    "cbr-0104a-workbook-3",
    ParseIssuanceRequest,
    ParsedIssuanceFile,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract source-local industry data with selection and validation scope.",
        inputs=(
            InputPort(
                "source",
                DataContract("cbr.industries.0104a.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.industries.0104a",)),
            ),
        ),
        outputs=(
            OutputPort(
                "file",
                DataContract("cbr.industries.0104a.parsed_file", 1, DataRole.EXTRACTS),
            ),
            OutputPort(
                "stream",
                DataContract("cbr.industries.0104a.stream", 1, DataRole.EXTRACTS),
                path="df_stream",
            ),
        ),
        parameters=("source_name", "source", "selection"),
    ),
)

BUILD_STREAM = OperationDefinition(
    f"{_DATASET}.build_stream",
    3,
    "cbr-0104a-stream-3",
    BuildIssuanceStreamRequest,
    IssuanceStreamResult,
    partial_allowed=True,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.CALCULATE),
        composition=True,
        summary="Parse supplied workbooks and combine a source-series stream with coverage evidence.",
        inputs=(
            InputPort(
                "sources",
                DataContract(
                    "cbr.industries.0104a.parse_requests", 1, DataRole.ORIGINALS
                ),
                path="sources",
            ),
        ),
        outputs=(
            OutputPort(
                "stream",
                DataContract("cbr.industries.0104a.stream", 1, DataRole.EXTRACTS),
                path="df_stream",
            ),
            OutputPort(
                "result",
                DataContract(
                    "cbr.industries.0104a.stream_result", 1, DataRole.EXTRACTS
                ),
            ),
        ),
        parameters=("continue_on_error", "selection"),
    ),
)

CALCULATE_APK = OperationDefinition(
    f"{_DATASET}.calculate_apk",
    2,
    "cbr-industry-apk-1",
    CalculateIssuanceApkRequest,
    IndustryApkCalculationResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE,),
        summary="Calculate the APK aggregate while retaining its source-series identity.",
        inputs=(
            InputPort(
                "stream",
                DataContract("cbr.industries.0104a.stream", 1, DataRole.EXTRACTS),
                path="stream",
            ),
        ),
        outputs=(
            OutputPort(
                "stream",
                DataContract("cbr.industries.0104a.stream", 1, DataRole.EXTRACTS),
                path="df_stream",
                qualifications=frozenset(("derived.apk",)),
            ),
        ),
    ),
)

PIVOT = OperationDefinition(
    f"{_DATASET}.build_pivots",
    2,
    "cbr-industry-pivot-1",
    PivotIssuanceRequest,
    IndustryPivotSetResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.VIEW,),
        summary="Construct industry pivots at the requested grain.",
        inputs=(
            InputPort(
                "stream",
                DataContract("cbr.industries.0104a.stream", 1, DataRole.EXTRACTS),
                path="stream",
            ),
        ),
        outputs=(
            OutputPort(
                "pivots",
                DataContract("cbr.industries.0104a.pivots", 1, DataRole.PRODUCTS),
            ),
        ),
        parameters=("pivot", "source", "industry_code"),
    ),
)

RENDER_INDUSTRY = OperationDefinition(
    f"{_DATASET}.render_industry",
    2,
    "cbr-0104a-xlsx-1",
    IssuanceWorkbookRequest,
    IssuanceWorkbookResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render one industry workbook from supplied data.",
        inputs=(
            InputPort(
                "stream",
                DataContract(
                    "cbr.industries.0104a.stream_result", 1, DataRole.EXTRACTS
                ),
                path="stream",
            ),
        ),
        outputs=(
            OutputPort(
                "workbook",
                DataContract("cbr.industries.0104a.workbook", 1, DataRole.PRODUCTS),
                path="representation",
            ),
        ),
        parameters=(
            "industry_code",
            "calculate_apk_if_missing",
            "include_metadata_sheet",
        ),
    ),
)

RENDER_INDUSTRIES = OperationDefinition(
    f"{_DATASET}.render_industries",
    1,
    "cbr-0104a-industry-batch-1",
    RenderIssuanceIndustriesRequest,
    IssuanceWorkbooksResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render independently qualified industry workbooks from supplied data.",
        inputs=(
            InputPort(
                "stream",
                DataContract(
                    "cbr.industries.0104a.stream_result", 1, DataRole.EXTRACTS
                ),
                path="stream",
            ),
        ),
        outputs=(
            OutputPort(
                "workbooks",
                DataContract("cbr.industries.0104a.workbooks", 1, DataRole.PRODUCTS),
            ),
        ),
        parameters=("industry_codes", "include_metadata_sheet"),
    ),
)
