"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.shared.evidence import AcquiredSource
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

_DATASET = "cbr.industries.0104a"

DISCOVER = _registry_definition('cbr.industries.0104a.discover', 1)

ACQUIRE = _registry_definition('cbr.industries.0104a.acquire', 1)

PARSE = _registry_definition('cbr.industries.0104a.parse', 3)

BUILD_STREAM = _registry_definition('cbr.industries.0104a.build_stream', 3)

CALCULATE_APK = _registry_definition('cbr.industries.0104a.calculate_apk', 2)

PIVOT = _registry_definition('cbr.industries.0104a.build_pivots', 2)

RENDER_INDUSTRY = _registry_definition('cbr.industries.0104a.render_industry', 2)

RENDER_INDUSTRIES = _registry_definition('cbr.industries.0104a.render_industries', 1)


from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import IntegrateIssuanceFlakesRequest

FLAKE_SNAPSHOT = _registry_definition('cbr.industries.0104a.flake_snapshot', 1)
READ_FLAKE_SNAPSHOT = _registry_definition('cbr.industries.0104a.read_flake_snapshot', 1)
STREAM_SNAPSHOT = _registry_definition('cbr.industries.0104a.stream_snapshot', 1)
READ_STREAM_SNAPSHOT = _registry_definition('cbr.industries.0104a.read_stream_snapshot', 1)
CALCULATION_SNAPSHOT = _registry_definition('cbr.industries.0104a.calculation_snapshot', 1)
READ_CALCULATION_SNAPSHOT = _registry_definition('cbr.industries.0104a.read_calculation_snapshot', 1)
VIEW_SNAPSHOT = _registry_definition('cbr.industries.0104a.view_snapshot', 1)
READ_VIEW_SNAPSHOT = _registry_definition('cbr.industries.0104a.read_view_snapshot', 1)

INTEGRATE_FLAKES = _registry_definition('cbr.industries.0104a.integrate_flakes', 1)

from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import RenderIssuancePivotsRequest

RENDER_PIVOTS = _registry_definition('cbr.industries.0104a.render_pivots', 1)
