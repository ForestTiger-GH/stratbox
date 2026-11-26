"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass


from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySpec as Cbr0105ADebtCorpIndustrySpec
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustryRegionSpec as Cbr0105ADebtCorpRegionSpec
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustryValidationIssue as Cbr0105ADebtCorpValidationIssue

from stratbox.domains.cbr.methods.tables.corporate_lending.debt.contracts import Cbr0105ADebtCorpSourceFailure

from stratbox.domains.cbr.methods.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink

from stratbox.domains.cbr.methods.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class Cbr0105ADebtCorpStreamResult:
    """Канонический результат построения потока ``01_05_A_Debt_corp``."""

    source_links: tuple[Cbr0105ADebtCorpSourceLink, ...]
    failures: tuple[Cbr0105ADebtCorpSourceFailure, ...]
    parsed_files: tuple[ParsedCbr0105ADebtCorpFile, ...]
    validation_issues: tuple[Cbr0105ADebtCorpValidationIssue, ...]
    df_stream: pd.DataFrame
    dates: tuple[str, ...]
    latest_report_date: str
    latest_discovered_report_date: str
    region_normalization_date: str
    region_normalization_is_latest_discovered: bool
    regions: tuple[Cbr0105ADebtCorpRegionSpec, ...]
    industries: tuple[Cbr0105ADebtCorpIndustrySpec, ...]
    rows_stream: int
    geography_method: str = "cbr.industry.published_geography"
    evidence: object | None = None
    stop_reason: str | None = None
    selection: IndustrySelection = IndustrySelection()
    source_validation_scope: str = "full"
    geography_reference: str = "cbr-industry-geography-2026-06-01"

    @property
    def sources_ok(self) -> bool:
        return not self.failures and self.stop_reason is None

    @property
    def validation_ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.validation_issues)

    @property
    def ok(self) -> bool:
        return self.sources_ok and self.validation_ok

    @property
    def is_partial(self) -> bool:
        return bool(self.failures or self.stop_reason) and bool(self.parsed_files)
