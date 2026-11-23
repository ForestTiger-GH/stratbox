"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.datasets import ComputationReceipt

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryRegionSpec as RegionSpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryValidationIssue as ValidationIssue
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection

from typing import TYPE_CHECKING
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
    selection: IndustrySelection = IndustrySelection()
    source_validation_scope: str = "full"
    geography_reference_version: str = "cbr-industry-geography-2026-06-01"
