"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.shared.evidence import AcquiredSource
from stratbox.core.execution.contracts import OperationDefinition
from ..common.operation_helpers import _TABLE_LIMITS
from .contracts import BuildIndustryStreamRequest, CalculateApkRequest, Cbr0105ADebtCorpApkCalculationResult, Cbr0105ADebtCorpIndustryWorkbookResult, Cbr0105ADebtCorpPivotSetResult, Cbr0105ADebtCorpPivotWorkbookResult, Cbr0105ADebtCorpSourceLink, Cbr0105ADebtCorpStreamResult, DiscoverIndustriesRequest, IndustryWorkbooksResult, ParseIndustryRequest, ParsedCbr0105ADebtCorpFile, PivotInput, RenderIndustriesRequest, RenderIndustryRequest, RenderPivotRequest

_DATASET = "cbr.industries.0105a"

_METHOD = "cbr-0105a-workbook-2"

_HTTP = frozenset({"http"})

DISCOVER = OperationDefinition(
    f"{_DATASET}.discover", 1, "cbr-0105a-index-1", DiscoverIndustriesRequest, tuple,
    optional_capabilities=frozenset({"http"}),
)

ACQUIRE = OperationDefinition(
    f"{_DATASET}.acquire",
    1,
    "cbr-0105a-source-1",
    Cbr0105ADebtCorpSourceLink,
    AcquiredSource,
    _HTTP,
)

PARSE = OperationDefinition(
    f"{_DATASET}.parse", 3, _METHOD + "-selective", ParseIndustryRequest, ParsedCbr0105ADebtCorpFile,
    limits=_TABLE_LIMITS,
)

BUILD_STREAM = OperationDefinition(
    f"{_DATASET}.build_stream",
    3,
    "cbr-0105a-stream-3",
    BuildIndustryStreamRequest,
    Cbr0105ADebtCorpStreamResult,
    partial_allowed=True,
    limits=_TABLE_LIMITS,
)

CALCULATE_APK = OperationDefinition(
    f"{_DATASET}.calculate_apk",
    2,
    "cbr-0105a-derived-apk-1",
    CalculateApkRequest,
    Cbr0105ADebtCorpApkCalculationResult,
    limits=_TABLE_LIMITS,
)

PIVOT = OperationDefinition(
    f"{_DATASET}.build_pivots",
    2,
    "cbr-0105a-pivots-1",
    PivotInput,
    Cbr0105ADebtCorpPivotSetResult,
    limits=_TABLE_LIMITS,
)

RENDER_PIVOTS = OperationDefinition(
    f"{_DATASET}.render_pivots",
    2,
    "cbr-0105a-pivot-xlsx-1",
    RenderPivotRequest,
    Cbr0105ADebtCorpPivotWorkbookResult,
    limits=_TABLE_LIMITS,
)

RENDER_INDUSTRY = OperationDefinition(
    f"{_DATASET}.render_industry",
    2,
    "cbr-0105a-industry-xlsx-1",
    RenderIndustryRequest,
    Cbr0105ADebtCorpIndustryWorkbookResult,
    limits=_TABLE_LIMITS,
)

RENDER_INDUSTRIES = OperationDefinition(
    f"{_DATASET}.render_industries", 1, "cbr-0105a-industry-batch-1",
    RenderIndustriesRequest, IndustryWorkbooksResult, limits=_TABLE_LIMITS,
)

