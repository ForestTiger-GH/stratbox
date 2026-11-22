"""Publisher identities, document evidence and caller-owned update state."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Literal
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import AcquiredSource, SourcePayload


@dataclass(frozen=True, slots=True)
class Variant:
    source_id: str
    asset_id: str
    title: str
    prefix: str
    suffix: str
    basis_hint: str = "unknown"
    periodicity: str = "unknown"


@dataclass(frozen=True, slots=True)
class SourceFamily:
    family_id: str
    title: str
    landing_url: str
    frequency: str
    formats: tuple[str, ...]
    default_source_id: str
    variants: tuple[Variant, ...]
    operations: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Asset:
    family_id: str
    source_id: str
    asset_id: str
    url: str
    filename: str
    format: str
    label: str
    recognition: Literal["registered_variant", "unclassified"]
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
