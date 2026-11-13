"""Typed source, observation and output contracts for CBR monthly corporate loan issuance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from stratbox.data import ComputationReceipt, Representation, SourcePayload
from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpApkCalculationResult,
    Cbr0105ADebtCorpIndustrySpec as IndustrySpec,
    Cbr0105ADebtCorpPivotRequest,
    Cbr0105ADebtCorpRegionSpec as RegionSpec,
    Cbr0105ADebtCorpValidationIssue as ValidationIssue,
)

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class IssuanceSheetSpec:
    code: str
    currency_scope: str
    currency_scope_name_ru: str
    workbook_sheet_name: str
    order: int
    measure: str = "new_loans"
    measure_name_ru: str = "Объем предоставленных кредитов"


@dataclass(frozen=True, slots=True)
class IssuanceSourceLink:
    source_id: str
    url: str
    source_name: str
    report_date: str
    reference_period: str


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


@dataclass(frozen=True, slots=True)
class BuildIssuanceStreamRequest:
    sources: tuple[ParseIssuanceRequest, ...]
    continue_on_error: bool = False


@dataclass(frozen=True, slots=True)
class IssuanceSourceFailure:
    stage: str
    source_id: str
    source_name: str
    code: str


@dataclass(frozen=True)
class ParsedIssuanceFile:
    source_id: str
    source_name: str
    source_url: str | None
    source_sha256: str
    report_date: str
    reference_period: str
    sheets: tuple[IssuanceSheetSpec, ...]
    industries: tuple[IndustrySpec, ...]
    regions: tuple[RegionSpec, ...]
    validation_issues: tuple[ValidationIssue, ...]
    df_stream: pd.DataFrame
    rows_stream: int
    evidence: ComputationReceipt | None = None
    unmapped_headers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class IssuanceStreamResult:
    source_links: tuple[IssuanceSourceLink, ...]
    failures: tuple[IssuanceSourceFailure, ...]
    parsed_files: tuple[ParsedIssuanceFile, ...]
    validation_issues: tuple[ValidationIssue, ...]
    df_stream: pd.DataFrame
    dates: tuple[str, ...]
    reference_periods: tuple[str, ...]
    latest_report_date: str
    latest_discovered_report_date: str
    region_normalization_date: str
    region_normalization_is_latest_discovered: bool
    regions: tuple[RegionSpec, ...]
    industries: tuple[IndustrySpec, ...]
    rows_stream: int
    evidence: ComputationReceipt | None = None
    stop_reason: str | None = None

    @property
    def is_partial(self) -> bool:
        return bool(self.failures or self.stop_reason) and bool(self.parsed_files)

    @property
    def ok(self) -> bool:
        return not self.failures and self.stop_reason is None and not any(
            x.severity == "error" for x in self.validation_issues
        )


@dataclass(frozen=True, slots=True)
class CalculateIssuanceApkRequest:
    stream: pd.DataFrame | IssuanceStreamResult | ParsedIssuanceFile


@dataclass(frozen=True, slots=True)
class PivotIssuanceRequest:
    stream: pd.DataFrame | IssuanceStreamResult | Cbr0105ADebtCorpApkCalculationResult
    pivot: Cbr0105ADebtCorpPivotRequest
    source: IssuanceStreamResult | None = None
    industry_code: str | None = None


@dataclass(frozen=True, slots=True)
class IssuanceWorkbookRequest:
    stream: IssuanceStreamResult
    industry_code: str = "apk"
    calculate_apk_if_missing: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True)
class IssuanceWorkbookResult:
    representation: Representation
    industry_code: str
    industry_name_ru: str
    sheet_names: tuple[str, ...]
    dates: tuple[str, ...]
    reference_periods: tuple[str, ...]
    rows_per_sheet: int

    @property
    def sheet_count(self) -> int:
        return sum(name != "_Параметры" for name in self.sheet_names)

    @property
    def ok(self) -> bool:
        return self.sheet_count == 3 and self.rows_per_sheet > 0
