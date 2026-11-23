"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.datasets import ComputationReceipt

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryRegionSpec as RegionSpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryValidationIssue as ValidationIssue
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection

from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import IssuanceSourceFailure

from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink

from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import ParsedIssuanceFile

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


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
    selection: IndustrySelection = IndustrySelection()
    source_validation_scope: str = "full"
    geography_reference_version: str = "cbr-industry-geography-2026-06-01"

    @property
    def is_partial(self) -> bool:
        return bool(self.failures or self.stop_reason) and bool(self.parsed_files)

    @property
    def ok(self) -> bool:
        return not self.failures and self.stop_reason is None and not any(
            x.severity == "error" for x in self.validation_issues
        )
