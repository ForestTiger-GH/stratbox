"""
contracts — контракты домена исторических данных по счетам эскроу.

Домен работает с ежемесячными Excel-публикациями ЦБ и разделяет:
- источники;
- скачивание и кэширование;
- нормализованный исторический набор данных;
- витринные представления;
- экспорт итогового workbook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping

import pandas as pd


SourceErrorPolicy = Literal["fail_fast", "collect_partial"]
RegionOrderMode = Literal["latest", "custom"]


@dataclass(frozen=True)
class EscrowIndicatorSpec:
    """Спецификация одного показателя из стандартной таблицы ЦБ."""

    code: str
    canonical_name: str
    sheet_code: str
    required_tokens: tuple[str, ...]
    order: int
    value_kind: str = "number"
    forbidden_tokens: tuple[str, ...] = ()
    is_required: bool = True
    is_output: bool = True


@dataclass(frozen=True)
class ResolvedEscrowColumn:
    """Сопоставление реального столбца Excel со спецификацией показателя."""

    source_name: str
    source_index: int
    spec: EscrowIndicatorSpec


@dataclass(frozen=True)
class EscrowParsedRow:
    """Распознанная строка таблицы по регионам."""

    source_row_index: int
    display_order: int
    row_kind: str
    entity_name: str
    federal_district_name: str | None
    region_number: int | None


@dataclass(frozen=True)
class ParsedEscrowFile:
    """Результат парсинга одного Excel-файла по счетам эскроу."""

    source_name: str
    file_date: str | None
    sheet_name: str
    header_row_index: int
    resolved_columns: list[ResolvedEscrowColumn]
    rows: list[EscrowParsedRow]
    df_rows: pd.DataFrame
    df_long: pd.DataFrame


@dataclass(frozen=True, slots=True)
class EscrowSourceLink:
    """Один найденный источник ежемесячного Excel-файла."""

    source_id: str
    url: str
    source_name: str
    file_date_hint: str | None = None


@dataclass(frozen=True, slots=True)
class EscrowSourceDownloadResult:
    """Успешно скачанный или прочитанный из кэша исходный файл."""

    source_id: str
    url: str
    source_name: str
    file_date_hint: str | None
    content: bytes = field(repr=False)
    size_bytes: int = 0
    used_url: str = ""
    final_url: str | None = None
    cache_path: str | None = None
    from_cache: bool = False


@dataclass(frozen=True, slots=True)
class EscrowSourceFailure:
    """Ошибка обработки одного источника ежемесячного файла."""

    source_id: str
    url: str
    source_name: str
    error: str
    status_code: int | None = None
    attempts_used: int = 0
    used_url: str | None = None
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class EscrowHistoryBuildRequest:
    """Запрос на построение исторического набора данных по счетам эскроу."""

    index_url: str
    source_cache_dir: str | None = None
    refresh: bool = False
    timeout: int = 60
    retries: int = 2
    backoff: float = 0.5
    min_bytes_ok: int = 512
    headers: Mapping[str, str] | None = None
    plugin_only: bool = True
    show_progress: bool = True
    source_error_policy: SourceErrorPolicy = "fail_fast"


@dataclass(frozen=True, slots=True)
class EscrowViewBuildRequest:
    """Запрос на построение витринного набора таблиц по истории эскроу."""

    regions_mode: RegionOrderMode = "latest"
    custom_regions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EscrowWorkbookExportRequest:
    """Запрос на экспорт workbook по данным эскроу."""

    out_path: str
    archive: bool = False
    archive_member_name: str | None = None
    show_progress: bool = True


@dataclass(frozen=True)
class EscrowHistoryResult:
    """Канонический результат построения исторического набора данных."""

    source_links: tuple[EscrowSourceLink, ...]
    downloaded_sources: tuple[EscrowSourceDownloadResult, ...]
    failures: tuple[EscrowSourceFailure, ...]
    parsed_files: tuple[ParsedEscrowFile, ...]
    df_long: pd.DataFrame
    dates: tuple[str, ...]
    indicators: tuple[str, ...]
    rows_long: int

    @property
    def ok(self) -> bool:
        return len(self.failures) == 0


@dataclass(frozen=True)
class EscrowPivotPack:
    """Набор витринных таблиц и их порядка для итогового workbook."""

    pivots: dict[str, pd.DataFrame]
    indicator_specs: tuple[EscrowIndicatorSpec, ...]
    region_order: tuple[str, ...]
    date_order: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EscrowExportResult:
    """Итог экспорта workbook по счетам эскроу."""

    output_path: str
    archive: bool
    source_files: tuple[str, ...]
    dates: tuple[str, ...]
    indicators: tuple[str, ...]
    regions: tuple[str, ...]
    rows_long: int
    source_links_count: int
    failure_count: int

    @property
    def ok(self) -> bool:
        return self.failure_count == 0


__all__ = [
    "EscrowIndicatorSpec",
    "ResolvedEscrowColumn",
    "EscrowParsedRow",
    "ParsedEscrowFile",
    "EscrowSourceLink",
    "EscrowSourceDownloadResult",
    "EscrowSourceFailure",
    "EscrowHistoryBuildRequest",
    "EscrowViewBuildRequest",
    "EscrowWorkbookExportRequest",
    "EscrowHistoryResult",
    "EscrowPivotPack",
    "EscrowExportResult",
    "SourceErrorPolicy",
    "RegionOrderMode",
]
