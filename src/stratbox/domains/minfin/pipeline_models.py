"""Domain contracts over existing Stratbox source, execution and artifact objects.

Stable logical source IDs, publisher markers, source bytes, an extracted table,
a cleaned series and notification candidates are distinct objects. Checkpoints
are supplied/persisted by the consumer, not owned by the pure domain library.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.representation import Representation
from .models import Asset, PublicationIndex, TableExtract


@dataclass(frozen=True, slots=True)
class SourceCheckpoint:
    source_id: str
    asset_id: str
    document_id: str | None
    modified_on: date | None
    asset_url: str
    original_identity: ByteIdentity
    flake_method_version: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateRequest:
    index: PublicationIndex
    checkpoints: tuple[SourceCheckpoint, ...] = ()
    selected_sources: tuple[str, ...] = ()
    retained_sources: frozenset[str] = frozenset()
    target: Literal["probe", "flake"] = "probe"
    method_version: str = "minfin.flake.v1"


@dataclass(frozen=True, slots=True)
class UpdateDecision:
    source_id: str
    asset: Asset | None
    state: Literal["initial", "unchanged", "revised", "indeterminate", "missing", "ambiguous"]
    download_required: bool
    processing_required: bool
    reason: str


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    family_id: str
    source_index_identity: ByteIdentity
    decisions: tuple[UpdateDecision, ...]
    inventory_coverage: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class FlakeColumn:
    source_column: int
    original_header: str
    period_id: str


@dataclass(frozen=True, slots=True)
class FlakeRow:
    source_row: int
    code: str
    indicator: str
    values: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class FlakeTable:
    family_id: str
    source_id: str
    original_identity: ByteIdentity
    sheet_name: str
    frequency: Literal["monthly", "quarterly", "annual"]
    value_basis: Literal["ytd", "annual", "stock"]
    columns: tuple[FlakeColumn, ...]
    rows: tuple[FlakeRow, ...]
    method_version: str = "minfin.flake.v1"
    unit_hint: str = "billion_rub"  # per-row units in NWF may differ; only headline metrics use RUB

    @property
    def latest_period(self) -> str:
        return self.columns[-1].period_id


@dataclass(frozen=True, slots=True)
class BuildFlakeRequest:
    extract: TableExtract
    source_id: str
    selected_sheet: str | None = None


@dataclass(frozen=True, slots=True)
class RenderFlakeRequest:
    flake: FlakeTable


@dataclass(frozen=True, slots=True)
class HeadlineMetric:
    metric_id: str
    label: str
    value: str
    previous_year_value: str | None
    yoy_pct: str | None
    comparison: Literal["comparable", "prior_missing", "prior_zero", "sign_change"]
    unit: str = "billion_rub"


@dataclass(frozen=True, slots=True)
class HeadlineSummary:
    family_id: str
    source_id: str
    period_id: str
    frequency: Literal["monthly", "quarterly", "annual"]
    value_basis: Literal["ytd", "annual", "stock"]
    original_identity: ByteIdentity
    flake_method_version: str
    metrics: tuple[HeadlineMetric, ...]


@dataclass(frozen=True, slots=True)
class SummaryRequest:
    flake: FlakeTable
    period_id: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationDatum:
    metric_id: str
    label: str
    value: str
    yoy_pct: str | None
    comparison: str
    unit: str


@dataclass(frozen=True, slots=True)
class NotificationFacts:
    """A channel-independent qualified candidate; never a delivery receipt."""
    event_key: str
    topic: str
    family_id: str
    source_id: str
    period_id: str
    published_on: date | None
    modified_on: date | None
    original_sha256: str
    source_url: str
    values: tuple[NotificationDatum, ...]
    publication_state: Literal["revised", "initial"]
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NoticePreparation:
    state: Literal["ready", "skipped"]
    facts: NotificationFacts | None
    reason: str


@dataclass(frozen=True, slots=True)
class NoticeRequest:
    summary: HeadlineSummary
    asset: Asset
    decision: UpdateDecision
    include_initial: bool = False


__all__ = (
    "SourceCheckpoint", "UpdateRequest", "UpdateDecision", "UpdatePlan",
    "FlakeColumn", "FlakeRow", "FlakeTable", "BuildFlakeRequest", "RenderFlakeRequest",
    "HeadlineMetric", "HeadlineSummary", "SummaryRequest", "NotificationDatum",
    "NotificationFacts", "NoticePreparation", "NoticeRequest",
)