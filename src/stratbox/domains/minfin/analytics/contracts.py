"""Source-local headline calculations and channel-neutral notification candidates."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Literal
from stratbox.shared.identity import ByteIdentity
from ..publications.contracts import Asset, UpdateDecision
from ..tables.contracts import FlakeTable
from ..publications.context import PublicationContext
from stratbox.shared.data.snapshots import DatasetSnapshot


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
    calculation_profile: str = ""
    calculation_version: int = 0
    flake_identity: ByteIdentity | None = None
    publication: PublicationContext | None = None


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
    publication_state: Literal["revised", "initial", "material_revision"]
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
    baseline_original_identity: ByteIdentity | None = None


@dataclass(frozen=True, slots=True)
class SummarySnapshotRequest:
    summary: HeadlineSummary
    dataset_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class ReadSummaryRequest:
    snapshot: DatasetSnapshot
