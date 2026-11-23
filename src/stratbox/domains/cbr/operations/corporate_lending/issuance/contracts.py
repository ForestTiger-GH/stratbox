"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from datetime import date

from stratbox.shared.evidence import SourcePayload

from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult

from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink

from stratbox.domains.cbr.integration.corporate_lending.issuance.contracts import IssuanceStreamResult

from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import ParsedIssuanceFile

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class DiscoverIssuanceRequest:
    index: SourcePayload | None = None
    date_from: str | date | None = None
    date_to: str | date | None = None


@dataclass(frozen=True, slots=True)
class ParseIssuanceRequest:
    payload: SourcePayload
    source_name: str
    source: IssuanceSourceLink | None = None
    selection: IndustrySelection = IndustrySelection()


@dataclass(frozen=True, slots=True)
class BuildIssuanceStreamRequest:
    sources: tuple[ParseIssuanceRequest, ...]
    continue_on_error: bool = False
    selection: IndustrySelection = IndustrySelection()


@dataclass(frozen=True, slots=True)
class IntegrateIssuanceFlakesRequest:
    flakes: tuple[ParsedIssuanceFile, ...]
    expected_report_dates: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class CalculateIssuanceApkRequest:
    stream: pd.DataFrame | IssuanceStreamResult | ParsedIssuanceFile


@dataclass(frozen=True, slots=True)
class PivotIssuanceRequest:
    stream: pd.DataFrame | IssuanceStreamResult | IndustryApkCalculationResult
    pivot: IndustryPivotRequest
    source: IssuanceStreamResult | None = None
    industry_code: str | None = None


@dataclass(frozen=True, slots=True)
class IssuanceWorkbookRequest:
    stream: IssuanceStreamResult
    industry_code: str = "apk"
    calculate_apk_if_missing: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class RenderIssuanceIndustriesRequest:
    stream: IssuanceStreamResult
    industry_codes: tuple[str, ...]
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class RenderIssuancePivotsRequest:
    tables: IndustryPivotSetResult
    industry_code: str
    industry_name_ru: str
    reference_periods: tuple[str, ...]
    include_metadata_sheet: bool = False
