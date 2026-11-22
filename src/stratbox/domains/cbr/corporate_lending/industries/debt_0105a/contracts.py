"""Контракты домена отраслевых таблиц Банка России.

Первая поддерживаемая серия — ``01_05_A_Debt_corp``:
задолженность, включая просроченную, по кредитам юридическим лицам-резидентам
и индивидуальным предпринимателям в региональном разрезе.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from typing import TYPE_CHECKING

from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload
from ..common.contracts import (
    IndustrySelection,
    IndustrySpec as Cbr0105ADebtCorpIndustrySpec,
    IndustryRegionSpec as Cbr0105ADebtCorpRegionSpec,
    IndustryValidationIssue as Cbr0105ADebtCorpValidationIssue,
    IndustryApkCalculationResult as Cbr0105ADebtCorpApkCalculationResult,
    IndustryPivotDimension as Cbr0105ADebtCorpPivotDimension,
    IndustryPivotRequest as Cbr0105ADebtCorpPivotRequest,
    IndustryPivotTable as Cbr0105ADebtCorpPivotTable,
    IndustryPivotSetResult as Cbr0105ADebtCorpPivotSetResult,
)

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
class Cbr0105ADebtCorpSourceLink:
    """Одна опубликованная книга серии ``01_05_A_Debt_corp``."""

    source_id: str
    url: str
    source_name: str
    report_date: str


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
    geography_method_version: str = "cbr-0105a-geography-1"
    evidence: ComputationReceipt | None = None
    stop_reason: str | None = None
    selection: IndustrySelection = IndustrySelection()
    source_validation_scope: str = "full"
    geography_reference_version: str = "cbr-industry-geography-2026-06-01"

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


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotWorkbookRequest:
    """Запрос на сохранение готового набора pivot-таблиц в одну книгу Excel."""

    freeze_headers: bool = True
    enable_auto_filter: bool = True
    adjust_column_widths: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotWorkbookResult:
    """Результат отдельной операции сохранения Excel-книги."""

    representation: Representation
    sheet_names: tuple[str, ...]
    sheet_count: int

    @property
    def ok(self) -> bool:
        return self.sheet_count > 0


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpIndustryWorkbookRequest:
    """Запрос на CBR-подобную книгу динамики одной отрасли по регионам."""

    industry_code: str = "apk"
    calculate_apk_if_missing: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpIndustryWorkbookResult:
    """Результат экспорта одной отрасли в шестилистовую CBR-подобную книгу."""

    representation: Representation
    industry_code: str
    industry_name_ru: str
    sheet_names: tuple[str, ...]
    sheet_count: int
    dates: tuple[str, ...]
    rows_per_sheet: int

    @property
    def ok(self) -> bool:
        return (
            bool(self.industry_code)
            and self.sheet_count == 6
            and self.rows_per_sheet > 0
        )


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


@dataclass(frozen=True)
class IndustryWorkbooksResult:
    items: tuple[Cbr0105ADebtCorpIndustryWorkbookResult, ...]

    @property
    def ok(self) -> bool:
        return bool(self.items) and all(item.ok for item in self.items)

