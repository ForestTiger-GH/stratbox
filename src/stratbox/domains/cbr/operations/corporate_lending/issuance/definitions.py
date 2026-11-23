"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.execution.semantics import technical_operation, ProcessingFunction

from stratbox.shared.evidence import AcquiredSource
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import BuildIssuanceStreamRequest
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import CalculateIssuanceApkRequest
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import DiscoverIssuanceRequest
from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink
from stratbox.domains.cbr.integration.corporate_lending.issuance.contracts import IssuanceStreamResult
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import IssuanceWorkbookRequest
from stratbox.domains.cbr.products.corporate_lending.issuance.contracts import IssuanceWorkbookResult
from stratbox.domains.cbr.products.corporate_lending.issuance.contracts import IssuanceWorkbooksResult
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import ParseIssuanceRequest
from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import ParsedIssuanceFile
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import PivotIssuanceRequest
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import RenderIssuanceIndustriesRequest
from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult
from stratbox.domains.cbr.operations.corporate_lending.industry.limits import TABLE_LIMITS as _TABLE_LIMITS

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
    optional_capabilities=frozenset({"http"}),
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
                alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS), DataContract("material.payload", 1)),
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
    "cbr-0104a-stream-4",
    BuildIssuanceStreamRequest,
    IssuanceStreamResult,
    partial_allowed=True,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE),
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
                DataContract("cbr.industries.0104a.stream", 1, DataRole.INTEGRATED),
                path="df_stream",
            ),
            OutputPort(
                "result",
                DataContract(
                    "cbr.industries.0104a.stream_result", 1, DataRole.INTEGRATED
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
                alternatives=(DataContract("cbr.industries.0104a.stream", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0104a.stream_result", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0104a.parsed_file", 1, DataRole.EXTRACTS),
                              DataContract("cbr.industries.0104a.calculation", 1, DataRole.INTEGRATED)),
            ),
        ),
        outputs=(
            OutputPort("result", DataContract("cbr.industries.0104a.calculation", 1, DataRole.INTEGRATED)),
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
                alternatives=(DataContract("cbr.industries.0104a.stream", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0104a.stream_result", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0104a.parsed_file", 1, DataRole.EXTRACTS),
                              DataContract("cbr.industries.0104a.calculation", 1, DataRole.INTEGRATED)),
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
        stages=(ProcessingStage.CALCULATE, ProcessingStage.VIEW, ProcessingStage.RENDER,),
        composition=True,
        summary="Render one industry workbook from supplied data.",
        inputs=(
            InputPort(
                "stream",
                DataContract(
                    "cbr.industries.0104a.stream_result", 1, DataRole.INTEGRATED
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
        stages=(ProcessingStage.CALCULATE, ProcessingStage.VIEW, ProcessingStage.RENDER,),
        composition=True,
        summary="Render independently qualified industry workbooks from supplied data.",
        inputs=(
            InputPort(
                "stream",
                DataContract(
                    "cbr.industries.0104a.stream_result", 1, DataRole.INTEGRATED
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


from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import IntegrateIssuanceFlakesRequest
from stratbox.domains.cbr.operations.corporate_lending.industry.snapshot_definitions import snapshot_definitions

FLAKE_SNAPSHOT, READ_FLAKE_SNAPSHOT = snapshot_definitions("0104a", "flake", ParsedIssuanceFile)
STREAM_SNAPSHOT, READ_STREAM_SNAPSHOT = snapshot_definitions("0104a", "stream", IssuanceStreamResult)
CALCULATION_SNAPSHOT, READ_CALCULATION_SNAPSHOT = snapshot_definitions("0104a", "calculation", IndustryApkCalculationResult)
VIEW_SNAPSHOT, READ_VIEW_SNAPSHOT = snapshot_definitions("0104a", "view", IndustryPivotSetResult)

INTEGRATE_FLAKES = OperationDefinition(
    f"{_DATASET}.integrate_flakes", 1, "cbr-industry-integration-1", IntegrateIssuanceFlakesRequest,
    IssuanceStreamResult, partial_allowed=True, limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.INTEGRATE,),
        summary="Integrate source-local flakes with explicit release selection and a pinned geography profile.",
        inputs=(InputPort("flakes", DataContract(f"{_DATASET}.parsed_files", 1, DataRole.EXTRACTS), path="flakes"),),
        outputs=(OutputPort("result", DataContract(f"{_DATASET}.stream_result", 1, DataRole.INTEGRATED)),
                 OutputPort("stream", DataContract(f"{_DATASET}.stream", 1, DataRole.INTEGRATED), path="df_stream")),
        parameters=("expected_report_dates",),
    ),
)

from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import RenderIssuancePivotsRequest

RENDER_PIVOTS = OperationDefinition(
    f"{_DATASET}.render_pivots", 1, "cbr-0104a-prepared-xlsx-1", RenderIssuancePivotsRequest,
    IssuanceWorkbookResult, limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,), summary="Render prepared issuance pivots without calculating or parsing source data.",
        inputs=(InputPort("tables", DataContract(f"{_DATASET}.pivots", 1, DataRole.PRODUCTS), path="tables"),),
        outputs=(OutputPort("workbook", DataContract(f"{_DATASET}.workbook", 1, DataRole.PRODUCTS), path="representation"),),
        parameters=("industry_code", "industry_name_ru", "reference_periods", "include_metadata_sheet"),
    ),
)
