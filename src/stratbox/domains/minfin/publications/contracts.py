"""Logical source families and publisher evidence, distinct from physical filenames.

Registry data names semantic sources and stable profiles. Profile implementations
own publisher-specific naming and layout rules. Checkpoints are caller-owned.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Literal
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import AcquiredSource, SourcePayload


@dataclass(frozen=True, slots=True)
class SourceSeries:
    source_id: str
    slot: str
    title: str
    periodicity: Literal["monthly", "quarterly", "annual", "unknown"]
    basis: Literal["ytd", "annual", "stock", "unknown"]
    kind: Literal["table", "document"]


@dataclass(frozen=True, slots=True)
class SourceProfileRefs:
    acquisition: str
    discovery: str
    identification: str
    table: str
    metrics: str


@dataclass(frozen=True, slots=True)
class SourceFamily:
    family_id: str
    title: str
    profiles: SourceProfileRefs
    series: tuple[SourceSeries, ...]

    @property
    def default_source_id(self) -> str:
        return self.family_id + ".attachments"

    def source(self, source_id: str) -> SourceSeries:
        for item in self.series:
            if item.source_id == source_id:
                return item
        raise ValueError("minfin.registry.unknown_series")

    def slot(self, slot: str) -> SourceSeries:
        for item in self.series:
            if item.slot == slot:
                return item
        raise ValueError("minfin.registry.unknown_slot")


@dataclass(frozen=True, slots=True)
class Asset:
    family_id: str
    source_id: str
    asset_id: str
    url: str
    filename: str
    format: str
    label: str
    recognition: Literal["registered_variant", "unclassified", "conflicted"]
    index_identity: ByteIdentity
    published_on: date | None = None
    modified_on: date | None = None
    document_id: str | None = None
    document_title: str = ""


@dataclass(frozen=True, slots=True)
class PublicationIndex:
    family_id: str
    assets: tuple[Asset, ...]
    index_identity: ByteIdentity
    coverage: Literal["unknown"] = "unknown"
    rejected_links: int = 0
    ambiguous_asset_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscoverRequest:
    family_id: str
    index: SourcePayload | None = None
    max_links: int = 2000
    page_url: str | None = None


@dataclass(frozen=True, slots=True)
class AcquireRequest:
    asset: Asset
    max_bytes: int = 64 * 1024 * 1024
    deadline_seconds: int = 60


@dataclass(frozen=True, slots=True)
class AcquiredAsset:
    asset: Asset
    source: AcquiredSource


@dataclass(frozen=True, slots=True)
class InspectRequest:
    before: PublicationIndex
    after: PublicationIndex


@dataclass(frozen=True, slots=True)
class Inspection:
    family_id: str
    added_candidates: tuple[str, ...]
    disappeared_candidates: tuple[str, ...]
    coverage: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class ReadableRequest:
    family_id: str
    payload: SourcePayload
    max_pages: int = 100
    format: Literal["pdf", "docx"] = "pdf"


@dataclass(frozen=True, slots=True)
class ReadableDocument:
    family_id: str
    source_identity: ByteIdentity
    pages: tuple[str, ...]
    coverage: Literal["text_only_partial"] = "text_only_partial"


@dataclass(frozen=True, slots=True)
class PublicationMarker:
    source_id: str
    asset_id: str
    document_id: str | None
    modified_on: date | None
    url: str


@dataclass(frozen=True, slots=True)
class MaterialVersion:
    source_id: str
    identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class ProcessingVersion:
    source_id: str
    method_version: str | None


@dataclass(frozen=True, slots=True)
class SourceCheckpoint:
    """One caller-held checkpoint with *independently inspectable* state layers.

    Keeping a single transport object does not conflate publisher changes with
    material bytes or processing versions. Physical commit remains caller-owned.
    """
    source_id: str
    asset_id: str
    document_id: str | None
    modified_on: date | None
    asset_url: str
    original_identity: ByteIdentity
    flake_method_version: str | None = None

    @property
    def publication(self) -> PublicationMarker:
        return PublicationMarker(self.source_id, self.asset_id, self.document_id,
                                 self.modified_on, self.asset_url)

    @property
    def material(self) -> MaterialVersion:
        return MaterialVersion(self.source_id, self.original_identity)

    @property
    def processing(self) -> ProcessingVersion:
        return ProcessingVersion(self.source_id, self.flake_method_version)


@dataclass(frozen=True, slots=True)
class UpdateRequest:
    index: PublicationIndex
    checkpoints: tuple[SourceCheckpoint, ...] = ()
    selected_sources: tuple[str, ...] = ()
    retained_sources: frozenset[str] = frozenset()
    target: Literal["probe", "flake"] = "probe"
    force_reprocess: bool = False
    force_refresh: bool = False


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


__all__ = (
    "SourceSeries", "SourceProfileRefs", "SourceFamily", "Asset", "PublicationIndex",
    "DiscoverRequest", "AcquireRequest", "AcquiredAsset", "InspectRequest", "Inspection",
    "ReadableRequest", "ReadableDocument", "SourceCheckpoint", "UpdateRequest", "UpdateDecision",
    "UpdatePlan", "PublicationMarker", "MaterialVersion", "ProcessingVersion",
)