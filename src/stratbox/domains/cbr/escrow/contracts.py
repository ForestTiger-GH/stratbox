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

from datetime import date
from typing import TYPE_CHECKING

from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity

if TYPE_CHECKING:
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
    evidence: ComputationReceipt | None = None
    unmapped_headers: tuple[str, ...] = ()
    df_cells: pd.DataFrame | None = None
    original_identity: ByteIdentity | None = None
    source_id: str | None = None
    method_version: str = "cbr-escrow-xlsx-flake-1"


@dataclass(frozen=True, slots=True)
class EscrowSourceLink:
    """Один найденный источник ежемесячного Excel-файла."""

    source_id: str
    url: str
    source_name: str
    file_date_hint: str | None = None
    format: str = "xlsx"
    extraction_status: str = "supported"
    profile_id: str = "cbr-escrow-xlsx-flake-1"


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
class DiscoverEscrowRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class ParseEscrowRequest:
    payload: SourcePayload
    source_name: str
    as_of: date | None = None


@dataclass(frozen=True, slots=True)
class EscrowHistoryBuildRequest:
    sources: tuple[ParseEscrowRequest, ...]
    continue_on_error: bool = False


@dataclass(frozen=True, slots=True)
class EscrowViewBuildRequest:
    """Запрос на построение витринного набора таблиц по истории эскроу."""

    regions_mode: RegionOrderMode = "latest"
    custom_regions: tuple[str, ...] = ()
    require_complete_history: bool = True
    missing_display: Literal["source_token", "blank"] = "source_token"


@dataclass(frozen=True)
class EscrowHistoryResult:
    """Канонический результат построения исторического набора данных."""

    failures: tuple[EscrowSourceFailure, ...]
    parsed_files: tuple[ParsedEscrowFile, ...]
    df_long: pd.DataFrame
    dates: tuple[str, ...]
    indicators: tuple[str, ...]
    rows_long: int
    evidence: ComputationReceipt | None = None
    stop_reason: str | None = None

    @property
    def ok(self) -> bool:
        return not self.failures and self.stop_reason is None


@dataclass(frozen=True)
class EscrowPivotPack:
    """Набор витринных таблиц и их порядка для итогового workbook."""

    pivots: dict[str, pd.DataFrame]
    indicator_specs: tuple[EscrowIndicatorSpec, ...]
    region_order: tuple[str, ...]
    date_order: tuple[str, ...]
    evidence: ComputationReceipt | None = None
    source_dataset: ByteIdentity | None = None
    coverage: SnapshotCoverage = SnapshotCoverage("unknown")
    missing_display: str = "source_token"
    row_metadata: tuple[tuple[str, str, str | None], ...] = ()


@dataclass(frozen=True)
class BuildEscrowViewsRequest:
    history: EscrowHistoryResult | EscrowDataset
    view: EscrowViewBuildRequest = EscrowViewBuildRequest()


@dataclass(frozen=True, slots=True)
class EscrowRelease:
    """One admitted publication and its interpretation profile."""

    period: str
    source_name: str
    source_id: str | None
    original_identity: ByteIdentity
    sheet_name: str
    method_version: str
    unmapped_headers: tuple[str, ...] = ()


@dataclass(frozen=True)
class EscrowDataset:
    """Integrated observations and period-specific row dimensions.

    Publication coverage is distinct from successful processing of the selected
    flakes. No live parsed-file objects are needed to prepare views.
    """

    observations: pd.DataFrame
    rows: pd.DataFrame
    releases: tuple[EscrowRelease, ...]
    indicator_specs: tuple[EscrowIndicatorSpec, ...]
    coverage: SnapshotCoverage
    selection_complete: bool = True
    evidence: ComputationReceipt | None = None


@dataclass(frozen=True, slots=True)
class IntegrateEscrowRequest:
    flakes: tuple[ParsedEscrowFile, ...]
    coverage: SnapshotCoverage = SnapshotCoverage(
        "unknown", "Selected publication flakes; publisher historical coverage is unspecified."
    )


@dataclass(frozen=True, slots=True)
class EscrowFlakeSnapshotRequest:
    flake: ParsedEscrowFile
    dataset_id: str = "cbr.escrow.flake"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class EscrowDatasetSnapshotRequest:
    dataset: EscrowDataset
    dataset_id: str = "cbr.escrow.integrated"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class EscrowViewSnapshotRequest:
    view: EscrowPivotPack
    dataset_id: str = "cbr.escrow.prepared_view"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadEscrowSnapshotRequest:
    snapshot: DatasetSnapshot
