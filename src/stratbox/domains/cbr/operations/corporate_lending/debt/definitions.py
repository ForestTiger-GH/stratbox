"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.shared.evidence import AcquiredSource
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

_DATASET = "cbr.industries.0105a"

_METHOD = "cbr-0105a-workbook-2"

_HTTP = frozenset({"http"})

DISCOVER = _registry_definition('cbr.industries.0105a.discover', 1)

ACQUIRE = _registry_definition('cbr.industries.0105a.acquire', 1)

PARSE = _registry_definition('cbr.industries.0105a.parse', 3)

BUILD_STREAM = _registry_definition('cbr.industries.0105a.build_stream', 3)

CALCULATE_APK = _registry_definition('cbr.industries.0105a.calculate_apk', 2)

PIVOT = _registry_definition('cbr.industries.0105a.build_pivots', 2)

RENDER_PIVOTS = _registry_definition('cbr.industries.0105a.render_pivots', 2)

RENDER_INDUSTRY = _registry_definition('cbr.industries.0105a.render_industry', 2)

RENDER_INDUSTRIES = _registry_definition('cbr.industries.0105a.render_industries', 1)


from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import IntegrateIndustryFlakesRequest

FLAKE_SNAPSHOT = _registry_definition('cbr.industries.0105a.flake_snapshot', 1)
READ_FLAKE_SNAPSHOT = _registry_definition('cbr.industries.0105a.read_flake_snapshot', 1)
STREAM_SNAPSHOT = _registry_definition('cbr.industries.0105a.stream_snapshot', 1)
READ_STREAM_SNAPSHOT = _registry_definition('cbr.industries.0105a.read_stream_snapshot', 1)
CALCULATION_SNAPSHOT = _registry_definition('cbr.industries.0105a.calculation_snapshot', 1)
READ_CALCULATION_SNAPSHOT = _registry_definition('cbr.industries.0105a.read_calculation_snapshot', 1)
VIEW_SNAPSHOT = _registry_definition('cbr.industries.0105a.view_snapshot', 1)
READ_VIEW_SNAPSHOT = _registry_definition('cbr.industries.0105a.read_view_snapshot', 1)

INTEGRATE_FLAKES = _registry_definition('cbr.industries.0105a.integrate_flakes', 1)
