"""Monthly corporate loan issuance by industry and region (01_04_A)."""

from stratbox.macrobanks.cbr_industries.contracts import IndustrySelection
from .contracts import (
    BuildIssuanceStreamRequest, CalculateIssuanceApkRequest, DiscoverIssuanceRequest,
    IssuanceSourceLink, IssuanceStreamResult, IssuanceWorkbookRequest,
    RenderIssuanceIndustriesRequest, IssuanceWorkbooksResult,
    ParseIssuanceRequest, PivotIssuanceRequest,
)
from .operations import (
    ACQUIRE, BUILD_STREAM, CALCULATE_APK, DISCOVER, PARSE, PIVOT,
    RENDER_INDUSTRY, RENDER_INDUSTRIES, acquire, build_pivots, build_stream, calculate_apk,
    discover, parse, render_industry, render_industries,
)
