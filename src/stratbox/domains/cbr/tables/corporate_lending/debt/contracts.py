"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

from stratbox.shared.data.datasets import ComputationReceipt

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySpec as Cbr0105ADebtCorpIndustrySpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryRegionSpec as Cbr0105ADebtCorpRegionSpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryValidationIssue as Cbr0105ADebtCorpValidationIssue

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


Cbr0105ADebtCorpFailureStage = Literal["download", "parse"]


Cbr0105ADebtCorpMeasure = Literal["debt", "overdue_debt"]


Cbr0105ADebtCorpCurrencyScope = Literal[
    "rubles",
    "foreign_currency_and_precious_metals",
    "total",
]


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpSheetSpec:
    """Смысл одного из шести листов серии ``01_05_A_Debt_corp``."""

    code: str
    measure: Cbr0105ADebtCorpMeasure
    measure_name_ru: str
    currency_scope: Cbr0105ADebtCorpCurrencyScope
    currency_scope_name_ru: str
    workbook_sheet_name: str
    order: int




@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpSourceFailure:
    """Ошибка получения или разбора одной книги."""

    stage: Cbr0105ADebtCorpFailureStage
    source_id: str
    url: str
    source_name: str
    report_date: str
    error: str
    status_code: int | None = None
    attempts_used: int = 0
    used_url: str | None = None
    final_url: str | None = None


@dataclass(frozen=True)
class ParsedCbr0105ADebtCorpFile:
    """Результат семантического разбора одной книги."""

    source_id: str
    source_name: str
    source_url: str | None
    source_sha256: str | None
    report_date: str
    sheets: tuple[Cbr0105ADebtCorpSheetSpec, ...]
    industries: tuple[Cbr0105ADebtCorpIndustrySpec, ...]
    regions: tuple[Cbr0105ADebtCorpRegionSpec, ...]
    validation_issues: tuple[Cbr0105ADebtCorpValidationIssue, ...]
    df_stream: pd.DataFrame
    rows_stream: int
    evidence: ComputationReceipt | None = None
    unmapped_headers: tuple[tuple[str, str], ...] = ()
    selection: IndustrySelection = IndustrySelection()
    source_validation_scope: str = "full"
    geography_reference_version: str = "cbr-industry-geography-2026-06-01"
