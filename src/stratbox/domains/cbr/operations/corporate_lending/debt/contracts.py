"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.evidence import SourcePayload

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult as Cbr0105ADebtCorpApkCalculationResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest as Cbr0105ADebtCorpPivotRequest
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult as Cbr0105ADebtCorpPivotSetResult

from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookRequest

from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpPivotWorkbookRequest

from stratbox.domains.cbr.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink

from stratbox.domains.cbr.integration.corporate_lending.debt.contracts import Cbr0105ADebtCorpStreamResult

from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class DiscoverIndustriesRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class ParseIndustryRequest:
    payload: SourcePayload
    source_name: str
    source: Cbr0105ADebtCorpSourceLink | None = None
    selection: IndustrySelection = IndustrySelection()


@dataclass(frozen=True, slots=True)
class BuildIndustryStreamRequest:
    sources: tuple[ParseIndustryRequest, ...]
    continue_on_error: bool = False
    selection: IndustrySelection = IndustrySelection()


@dataclass(frozen=True, slots=True)
class IntegrateIndustryFlakesRequest:
    flakes: tuple[ParsedCbr0105ADebtCorpFile, ...]
    expected_report_dates: tuple[str, ...] | None = None


@dataclass(frozen=True)
class CalculateApkRequest:
    stream: pd.DataFrame | Cbr0105ADebtCorpStreamResult | ParsedCbr0105ADebtCorpFile


@dataclass(frozen=True)
class PivotInput:
    stream: pd.DataFrame | Cbr0105ADebtCorpStreamResult | Cbr0105ADebtCorpApkCalculationResult
    pivot: Cbr0105ADebtCorpPivotRequest
    source: Cbr0105ADebtCorpStreamResult | None = None
    industry_code: str | None = None


@dataclass(frozen=True)
class RenderPivotRequest:
    tables: Cbr0105ADebtCorpPivotSetResult
    format: Cbr0105ADebtCorpPivotWorkbookRequest = Cbr0105ADebtCorpPivotWorkbookRequest()


@dataclass(frozen=True)
class RenderIndustryRequest:
    stream: Cbr0105ADebtCorpStreamResult
    format: Cbr0105ADebtCorpIndustryWorkbookRequest = Cbr0105ADebtCorpIndustryWorkbookRequest()


@dataclass(frozen=True, slots=True)
class RenderIndustriesRequest:
    stream: Cbr0105ADebtCorpStreamResult
    industry_codes: tuple[str, ...]
    include_metadata_sheet: bool = False
