"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.shared.evidence import AcquiredSource
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import BuildIssuanceStreamRequest, CalculateIssuanceApkRequest, DiscoverIssuanceRequest, IssuanceSourceLink, IssuanceStreamResult, IssuanceWorkbookRequest, IssuanceWorkbookResult, IssuanceWorkbooksResult, ParseIssuanceRequest, ParsedIssuanceFile, PivotIssuanceRequest, RenderIssuanceIndustriesRequest
from ..common.contracts import IndustryApkCalculationResult, IndustryPivotSetResult
from stratbox.domains.cbr.corporate_lending.industries.common.operation_helpers import _TABLE_LIMITS

_DATASET = "cbr.industries.0104a"

DISCOVER = OperationDefinition(f"{_DATASET}.discover", 1, "cbr-0104a-index-1", DiscoverIssuanceRequest, tuple)

ACQUIRE = OperationDefinition(f"{_DATASET}.acquire", 1, "cbr-0104a-source-1", IssuanceSourceLink,
                              AcquiredSource, frozenset({"http"}))

PARSE = OperationDefinition(f"{_DATASET}.parse", 3, "cbr-0104a-workbook-3", ParseIssuanceRequest,
                            ParsedIssuanceFile, limits=_TABLE_LIMITS)

BUILD_STREAM = OperationDefinition(f"{_DATASET}.build_stream", 3, "cbr-0104a-stream-3",
                                   BuildIssuanceStreamRequest, IssuanceStreamResult,
                                   partial_allowed=True, limits=_TABLE_LIMITS)

CALCULATE_APK = OperationDefinition(f"{_DATASET}.calculate_apk", 2, "cbr-industry-apk-1",
                                    CalculateIssuanceApkRequest, IndustryApkCalculationResult,
                                    limits=_TABLE_LIMITS)

PIVOT = OperationDefinition(f"{_DATASET}.build_pivots", 2, "cbr-industry-pivot-1",
                            PivotIssuanceRequest, IndustryPivotSetResult, limits=_TABLE_LIMITS)

RENDER_INDUSTRY = OperationDefinition(f"{_DATASET}.render_industry", 2, "cbr-0104a-xlsx-1",
                                      IssuanceWorkbookRequest, IssuanceWorkbookResult, limits=_TABLE_LIMITS)

RENDER_INDUSTRIES = OperationDefinition(
    f"{_DATASET}.render_industries", 1, "cbr-0104a-industry-batch-1",
    RenderIssuanceIndustriesRequest, IssuanceWorkbooksResult, limits=_TABLE_LIMITS,
)

