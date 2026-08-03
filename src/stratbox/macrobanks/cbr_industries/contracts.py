"""Контракты домена отраслевых таблиц Банка России.

Первая поддерживаемая серия — ``01_05_A_Debt_corp``:
задолженность, включая просроченную, по кредитам юридическим лицам-резидентам
и индивидуальным предпринимателям в региональном разрезе.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping

import pandas as pd


Cbr0105ADebtCorpSourceErrorPolicy = Literal["fail_fast", "collect_partial"]
Cbr0105ADebtCorpFailureStage = Literal["download", "parse"]
Cbr0105ADebtCorpMeasure = Literal["debt", "overdue_debt"]
Cbr0105ADebtCorpCurrencyScope = Literal[
    "rubles",
    "foreign_currency_and_precious_metals",
    "total",
]
Cbr0105ADebtCorpPivotDimension = Literal[
    "report_date",
    "region_code",
    "industry_code",
    "measure",
    "currency_scope",
]


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpSheetSpec:
    """Смысл одного из шести листов серии ``01_05_A_Debt_corp``."""

    code: str
    measure: Cbr0105ADebtCorpMeasure
    measure_name_ru: str
    currency_scope: Cbr0105ADebtCorpCurrencyScope
    currency_scope_name_ru: str
    order: int


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpIndustrySpec:
    """Один отраслевой столбец таблицы Банка России."""

    code: str
    canonical_name_ru: str
    parent_code: str | None
    hierarchy_level: int
    order: int


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpRegionSpec:
    """Одна географическая строка серии ``01_05_A_Debt_corp``."""

    code: str
    source_name: str
    canonical_name: str
    region_kind: str
    federal_district_name: str | None
    order: int


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpSourceLink:
    """Одна опубликованная книга серии ``01_05_A_Debt_corp``."""

    source_id: str
    url: str
    source_name: str
    report_date: str


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpDownloadedSource:
    """Скачанный или прочитанный из кэша исходный XLSX."""

    source_id: str
    url: str
    source_name: str
    report_date: str
    content: bytes = field(repr=False)
    size_bytes: int = 0
    sha256: str = ""
    used_url: str = ""
    final_url: str | None = None
    cache_path: str | None = None
    from_cache: bool = False


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


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpValidationIssue:
    """Отклонение, найденное в структуре или значениях публикации."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    count: int = 1
    details: Mapping[str, object] = field(default_factory=dict)


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


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpDownloadRequest:
    """Запрос на обнаружение и скачивание книг выбранного периода."""

    index_url: str
    date_from: str | None = None
    date_to: str | None = None
    source_cache_dir: str | None = None
    refresh: bool = False
    timeout: int = 60
    retries: int = 2
    backoff: float = 0.5
    min_bytes_ok: int = 512
    headers: Mapping[str, str] | None = None
    plugin_only: bool = True
    show_progress: bool = True
    source_error_policy: Cbr0105ADebtCorpSourceErrorPolicy = "fail_fast"


@dataclass(frozen=True)
class Cbr0105ADebtCorpDownloadBatchResult:
    """Результат операции скачивания набора исходных книг."""

    source_links: tuple[Cbr0105ADebtCorpSourceLink, ...]
    downloaded_sources: tuple[Cbr0105ADebtCorpDownloadedSource, ...]
    failures: tuple[Cbr0105ADebtCorpSourceFailure, ...]

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def is_partial(self) -> bool:
        return bool(self.failures) and bool(self.downloaded_sources)


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpStreamBuildRequest:
    """Запрос на построение нормализованного потокового набора."""

    index_url: str
    date_from: str | None = None
    date_to: str | None = None
    source_cache_dir: str | None = None
    refresh: bool = False
    timeout: int = 60
    retries: int = 2
    backoff: float = 0.5
    min_bytes_ok: int = 512
    headers: Mapping[str, str] | None = None
    plugin_only: bool = True
    show_progress: bool = True
    source_error_policy: Cbr0105ADebtCorpSourceErrorPolicy = "fail_fast"


@dataclass(frozen=True)
class Cbr0105ADebtCorpStreamResult:
    """Канонический результат построения потока ``01_05_A_Debt_corp``."""

    source_links: tuple[Cbr0105ADebtCorpSourceLink, ...]
    downloaded_sources: tuple[Cbr0105ADebtCorpDownloadedSource, ...]
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

    @property
    def sources_ok(self) -> bool:
        return not self.failures

    @property
    def validation_ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.validation_issues)

    @property
    def ok(self) -> bool:
        return self.sources_ok and self.validation_ok

    @property
    def is_partial(self) -> bool:
        return bool(self.failures) and bool(self.parsed_files)


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotRequest:
    """Запрос на построение набора двумерных таблиц из отфильтрованного потока.

    Все смысловые измерения, которые не назначены строками, столбцами или листами,
    обязаны быть заранее отфильтрованы до одного значения.
    """

    row_dimension: Cbr0105ADebtCorpPivotDimension
    column_dimension: Cbr0105ADebtCorpPivotDimension
    value_columns: tuple[str, ...] = ("value",)
    sheet_dimensions: tuple[Cbr0105ADebtCorpPivotDimension, ...] = ()
    require_complete_stream: bool = True
    max_sheet_count: int = 100


@dataclass(frozen=True)
class Cbr0105ADebtCorpPivotTable:
    """Одна двумерная таблица будущего листа workbook."""

    sheet_key: tuple[tuple[str, object], ...]
    suggested_sheet_name: str
    row_dimension: Cbr0105ADebtCorpPivotDimension
    column_dimension: Cbr0105ADebtCorpPivotDimension
    value_columns: tuple[str, ...]
    df_table: pd.DataFrame
    rows: int
    data_columns: int
    missing_values: int


@dataclass(frozen=True)
class Cbr0105ADebtCorpPivotSetResult:
    """Набор таблиц, построенный одной универсальной pivot-операцией."""

    tables: tuple[Cbr0105ADebtCorpPivotTable, ...]
    row_dimension: Cbr0105ADebtCorpPivotDimension
    column_dimension: Cbr0105ADebtCorpPivotDimension
    value_columns: tuple[str, ...]
    sheet_dimensions: tuple[Cbr0105ADebtCorpPivotDimension, ...]
    fixed_dimensions: tuple[tuple[str, object], ...]
    source_rows: int
    table_count: int
    is_partial: bool

    @property
    def ok(self) -> bool:
        return bool(self.tables)


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotWorkbookRequest:
    """Запрос на сохранение готового набора pivot-таблиц в одну книгу Excel."""

    out_path: str
    overwrite: bool = False
    freeze_headers: bool = True
    enable_auto_filter: bool = True
    adjust_column_widths: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotWorkbookResult:
    """Результат отдельной операции сохранения Excel-книги."""

    output_path: str
    sheet_names: tuple[str, ...]
    sheet_count: int
    file_size: int
    sha256: str

    @property
    def ok(self) -> bool:
        return bool(self.output_path) and self.sheet_count > 0


__all__ = [
    "Cbr0105ADebtCorpCurrencyScope",
    "Cbr0105ADebtCorpDownloadBatchResult",
    "Cbr0105ADebtCorpDownloadedSource",
    "Cbr0105ADebtCorpDownloadRequest",
    "Cbr0105ADebtCorpFailureStage",
    "Cbr0105ADebtCorpIndustrySpec",
    "Cbr0105ADebtCorpMeasure",
    "Cbr0105ADebtCorpPivotDimension",
    "Cbr0105ADebtCorpPivotRequest",
    "Cbr0105ADebtCorpPivotSetResult",
    "Cbr0105ADebtCorpPivotTable",
    "Cbr0105ADebtCorpPivotWorkbookRequest",
    "Cbr0105ADebtCorpPivotWorkbookResult",
    "Cbr0105ADebtCorpRegionSpec",
    "Cbr0105ADebtCorpSheetSpec",
    "Cbr0105ADebtCorpSourceErrorPolicy",
    "Cbr0105ADebtCorpSourceFailure",
    "Cbr0105ADebtCorpSourceLink",
    "Cbr0105ADebtCorpStreamBuildRequest",
    "Cbr0105ADebtCorpStreamResult",
    "Cbr0105ADebtCorpValidationIssue",
    "ParsedCbr0105ADebtCorpFile",
]
