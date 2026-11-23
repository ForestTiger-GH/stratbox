"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.execution.semantics import technical_operation, ProcessingFunction

from stratbox.shared.evidence import AcquiredSource
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.domains.cbr.operations.corporate_lending.industry.limits import TABLE_LIMITS as _TABLE_LIMITS
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import BuildIndustryStreamRequest
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import CalculateApkRequest
from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult as Cbr0105ADebtCorpApkCalculationResult
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult as Cbr0105ADebtCorpPivotSetResult
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpPivotWorkbookResult
from stratbox.domains.cbr.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink
from stratbox.domains.cbr.integration.corporate_lending.debt.contracts import Cbr0105ADebtCorpStreamResult
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import DiscoverIndustriesRequest
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import IndustryWorkbooksResult
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import ParseIndustryRequest
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import PivotInput
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderIndustriesRequest
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderIndustryRequest
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderPivotRequest

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

_DATASET = "cbr.industries.0105a"

_METHOD = "cbr-0105a-workbook-2"

_HTTP = frozenset({"http"})

DISCOVER = OperationDefinition(
    f"{_DATASET}.discover",
    1,
    "cbr-0105a-index-1",
    DiscoverIndustriesRequest,
    tuple,
    optional_capabilities=frozenset({"http"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.DISCOVER,),
        summary="Discover the selected stock or flow publication series.",
        inputs=(
            InputPort(
                "index",
                DataContract(
                    "cbr.industries.0105a.index_material", 1, DataRole.ORIGINALS
                ),
                path="index",
                required=False,
            ),
        ),
        outputs=(
            OutputPort("sources", DataContract("cbr.industries.0105a.index", 1, None)),
        ),
    ),
)

ACQUIRE = OperationDefinition(
    f"{_DATASET}.acquire",
    1,
    "cbr-0105a-source-1",
    Cbr0105ADebtCorpSourceLink,
    AcquiredSource,
    _HTTP,
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Acquire a selected industry workbook under its own publication contract.",
        inputs=(
            InputPort("source", DataContract("cbr.industries.0105a.source", 1, None)),
        ),
        outputs=(
            OutputPort(
                "source",
                DataContract("cbr.industries.0105a.original", 1, DataRole.ORIGINALS),
                path="payload",
                qualifications=frozenset(("source.cbr.industries.0105a",)),
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
    _METHOD + "-selective",
    ParseIndustryRequest,
    ParsedCbr0105ADebtCorpFile,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Extract source-local industry data with selection and validation scope.",
        inputs=(
            InputPort(
                "source",
                DataContract("cbr.industries.0105a.original", 1, DataRole.ORIGINALS),
                path="payload",
                alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS), DataContract("material.payload", 1)),
            ),
        ),
        outputs=(
            OutputPort(
                "file",
                DataContract("cbr.industries.0105a.parsed_file", 1, DataRole.EXTRACTS),
            ),
            OutputPort(
                "stream",
                DataContract("cbr.industries.0105a.stream", 1, DataRole.EXTRACTS),
                path="df_stream",
            ),
        ),
        parameters=("source_name", "source", "selection"),
    ),
)

BUILD_STREAM = OperationDefinition(
    f"{_DATASET}.build_stream",
    3,
    "cbr-0105a-stream-4",
    BuildIndustryStreamRequest,
    Cbr0105ADebtCorpStreamResult,
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
                    "cbr.industries.0105a.parse_requests", 1, DataRole.ORIGINALS
                ),
                path="sources",
            ),
        ),
        outputs=(
            OutputPort(
                "stream",
                DataContract("cbr.industries.0105a.stream", 1, DataRole.INTEGRATED),
                path="df_stream",
            ),
            OutputPort(
                "result",
                DataContract(
                    "cbr.industries.0105a.stream_result", 1, DataRole.INTEGRATED
                ),
            ),
        ),
        parameters=("continue_on_error", "selection"),
    ),
)

CALCULATE_APK = OperationDefinition(
    f"{_DATASET}.calculate_apk",
    2,
    "cbr-0105a-derived-apk-1",
    CalculateApkRequest,
    Cbr0105ADebtCorpApkCalculationResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE,),
        summary="Calculate the APK aggregate while retaining its source-series identity.",
        inputs=(
            InputPort(
                "stream",
                DataContract("cbr.industries.0105a.stream", 1, DataRole.EXTRACTS),
                path="stream",
                alternatives=(DataContract("cbr.industries.0105a.stream", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0105a.stream_result", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0105a.parsed_file", 1, DataRole.EXTRACTS),
                              DataContract("cbr.industries.0105a.calculation", 1, DataRole.INTEGRATED)),
            ),
        ),
        outputs=(
            OutputPort("result", DataContract("cbr.industries.0105a.calculation", 1, DataRole.INTEGRATED)),
            OutputPort(
                "stream",
                DataContract("cbr.industries.0105a.stream", 1, DataRole.EXTRACTS),
                path="df_stream",
                qualifications=frozenset(("derived.apk",)),
            ),
        ),
    ),
)

PIVOT = OperationDefinition(
    f"{_DATASET}.build_pivots",
    2,
    "cbr-0105a-pivots-1",
    PivotInput,
    Cbr0105ADebtCorpPivotSetResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.VIEW,),
        summary="Construct industry pivots at the requested grain.",
        inputs=(
            InputPort(
                "stream",
                DataContract("cbr.industries.0105a.stream", 1, DataRole.EXTRACTS),
                path="stream",
                alternatives=(DataContract("cbr.industries.0105a.stream", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0105a.stream_result", 1, DataRole.INTEGRATED),
                              DataContract("cbr.industries.0105a.parsed_file", 1, DataRole.EXTRACTS),
                              DataContract("cbr.industries.0105a.calculation", 1, DataRole.INTEGRATED)),
            ),
        ),
        outputs=(
            OutputPort(
                "pivots",
                DataContract("cbr.industries.0105a.pivots", 1, DataRole.PRODUCTS),
            ),
        ),
        parameters=("pivot", "source", "industry_code"),
    ),
)

RENDER_PIVOTS = OperationDefinition(
    f"{_DATASET}.render_pivots",
    2,
    "cbr-0105a-pivot-xlsx-1",
    RenderPivotRequest,
    Cbr0105ADebtCorpPivotWorkbookResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render supplied industry pivots into a workbook.",
        inputs=(
            InputPort(
                "pivots",
                DataContract("cbr.industries.0105a.pivots", 1, DataRole.PRODUCTS),
                path="tables",
            ),
        ),
        outputs=(
            OutputPort(
                "workbook",
                DataContract("cbr.industries.0105a.workbook", 1, DataRole.PRODUCTS),
                path="representation",
            ),
        ),
        parameters=("format",),
    ),
)

RENDER_INDUSTRY = OperationDefinition(
    f"{_DATASET}.render_industry",
    2,
    "cbr-0105a-industry-xlsx-1",
    RenderIndustryRequest,
    Cbr0105ADebtCorpIndustryWorkbookResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE, ProcessingStage.VIEW, ProcessingStage.RENDER,),
        composition=True,
        summary="Render one industry workbook from supplied data.",
        inputs=(
            InputPort(
                "stream",
                DataContract(
                    "cbr.industries.0105a.stream_result", 1, DataRole.INTEGRATED
                ),
                path="stream",
            ),
        ),
        outputs=(
            OutputPort(
                "workbook",
                DataContract("cbr.industries.0105a.workbook", 1, DataRole.PRODUCTS),
                path="representation",
            ),
        ),
        parameters=("format",),
    ),
)

RENDER_INDUSTRIES = OperationDefinition(
    f"{_DATASET}.render_industries",
    1,
    "cbr-0105a-industry-batch-1",
    RenderIndustriesRequest,
    IndustryWorkbooksResult,
    limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE, ProcessingStage.VIEW, ProcessingStage.RENDER,),
        composition=True,
        summary="Render independently qualified industry workbooks from supplied data.",
        inputs=(
            InputPort(
                "stream",
                DataContract(
                    "cbr.industries.0105a.stream_result", 1, DataRole.INTEGRATED
                ),
                path="stream",
            ),
        ),
        outputs=(
            OutputPort(
                "workbooks",
                DataContract("cbr.industries.0105a.workbooks", 1, DataRole.PRODUCTS),
            ),
        ),
        parameters=("industry_codes", "include_metadata_sheet"),
    ),
)


from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import IntegrateIndustryFlakesRequest
from stratbox.domains.cbr.operations.corporate_lending.industry.snapshot_definitions import snapshot_definitions

FLAKE_SNAPSHOT, READ_FLAKE_SNAPSHOT = snapshot_definitions("0105a", "flake", ParsedCbr0105ADebtCorpFile)
STREAM_SNAPSHOT, READ_STREAM_SNAPSHOT = snapshot_definitions("0105a", "stream", Cbr0105ADebtCorpStreamResult)
CALCULATION_SNAPSHOT, READ_CALCULATION_SNAPSHOT = snapshot_definitions("0105a", "calculation", Cbr0105ADebtCorpApkCalculationResult)
VIEW_SNAPSHOT, READ_VIEW_SNAPSHOT = snapshot_definitions("0105a", "view", Cbr0105ADebtCorpPivotSetResult)

INTEGRATE_FLAKES = OperationDefinition(
    f"{_DATASET}.integrate_flakes", 1, "cbr-industry-integration-1", IntegrateIndustryFlakesRequest,
    Cbr0105ADebtCorpStreamResult, partial_allowed=True, limits=_TABLE_LIMITS,
    processing=OperationSemantics(
        stages=(ProcessingStage.INTEGRATE,),
        summary="Integrate source-local flakes with explicit release selection and a pinned geography profile.",
        inputs=(InputPort("flakes", DataContract(f"{_DATASET}.parsed_files", 1, DataRole.EXTRACTS), path="flakes"),),
        outputs=(OutputPort("result", DataContract(f"{_DATASET}.stream_result", 1, DataRole.INTEGRATED)),
                 OutputPort("stream", DataContract(f"{_DATASET}.stream", 1, DataRole.INTEGRATED), path="df_stream")),
        parameters=("expected_report_dates",),
    ),
)
