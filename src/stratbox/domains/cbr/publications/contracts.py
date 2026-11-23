"""Logical series, discovered instances and explicit caller-supplied originals."""
from __future__ import annotations

from dataclasses import dataclass, field

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import SnapshotCoverage, identifier
from stratbox.shared.evidence import AcquisitionReceipt, SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.materials import MaterialArtifact
from stratbox.shared.source_publications import SourceAssetIdentity


@dataclass(frozen=True, slots=True)
class SourceSeries:
    series_id: str
    family_id: str
    title: str
    issue_model: str
    formats: tuple[str, ...]
    acquisition_profile: str
    extraction_profile: str | None = None
    normalization_profile: str | None = None
    table_profile: str | None = None
    integration_profile: str | None = None
    product_profile: str | None = None

    def __post_init__(self):
        for value in (self.series_id, self.family_id, self.acquisition_profile):
            identifier(value)
        if self.issue_model not in {"rolling", "dated", "capture"} or not self.formats or not self.title:
            raise ValueError("cbr.registry.series_invalid")
        for value in (self.extraction_profile, self.normalization_profile, self.table_profile,
                      self.integration_profile, self.product_profile):
            if value is not None:
                identifier(value)


@dataclass(frozen=True, slots=True)
class AcquisitionProfile:
    profile_id: str
    kind: str
    default_url: str
    filename_pattern: str | None = None

    def __post_init__(self):
        from urllib.parse import urlsplit
        identifier(self.profile_id)
        value = urlsplit(self.default_url)
        if (self.kind not in {"fixed", "page", "index", "escrow_index", "territorial_index"}
                or value.scheme != "https" or value.hostname not in {"cbr.ru", "www.cbr.ru"}
                or value.username or value.password or value.query or value.fragment):
            raise ValueError("cbr.profile.acquisition_invalid")
        if self.kind == "index" and not self.filename_pattern:
            raise ValueError("cbr.profile.pattern_required")


@dataclass(frozen=True, slots=True)
class ProcessingProfile:
    profile_id: str
    operation_id: str
    formats: tuple[str, ...]
    scope: str

    def __post_init__(self):
        identifier(self.profile_id)
        identifier(self.operation_id)
        if not self.formats or not self.scope:
            raise ValueError("cbr.profile.processing_invalid")


@dataclass(frozen=True, slots=True)
class PublicationAsset:
    """One publication/format candidate with all observed physical routes.

    Alternative routes retain unresolved source ambiguity. Their byte equality,
    availability and revision order require acquisition; discovery asserts none.
    """
    series_id: str
    issue_id: str | None
    asset_id: str
    url: str
    format: str
    recognition: str
    extraction_profile: str | None = None
    alternative_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicationInventory:
    series_id: str
    assets: tuple[PublicationAsset, ...]
    index_identity: ByteIdentity | None
    coverage: SnapshotCoverage
    rejected_links: int = 0


@dataclass(frozen=True, slots=True)
class ListSourcesRequest:
    family_id: str | None = None


@dataclass(frozen=True, slots=True)
class DiscoverRequest:
    series_id: str
    index: SourcePayload | None = None
    page_url: str | None = None
    max_links: int = 10_000


@dataclass(frozen=True, slots=True)
class IdentifyRequest:
    series_id: str
    issue_id: str
    payload: SourcePayload
    format: str
    asset_id: str = "main"


@dataclass(frozen=True, slots=True)
class IdentifiedOriginal:
    asset: SourceAssetIdentity
    payload: SourcePayload
    format: str
    identification: str = "caller_context_and_verified_format"
    lineage: tuple[UsedInputReceipt, ...] = ()
    acquisition: AcquisitionReceipt | None = None
    artifact: MaterialArtifact = field(init=False)

    def __post_init__(self):
        if self.acquisition is not None and (
            self.acquisition.identity != self.payload.identity
            or self.acquisition.media_type != self.payload.media_type
            or self.acquisition.source_id != self.asset.series_id
        ):
            raise ValueError("cbr.original.acquisition_mismatch")
        object.__setattr__(self, "artifact", MaterialArtifact(DataContract("cbr.publication.original", 1, DataRole.ORIGINALS),
            Representation("cbr.original." + self.format, 1, self.payload.media_type,
                           self.payload.data, self.payload.charset), self.lineage,
            self.asset.series_id, self.asset))


@dataclass(frozen=True, slots=True)
class SelectPublicationRequest:
    inventory: PublicationInventory
    issue_id: str | None = None
    format: str | None = None
    asset_id: str = "main"
    url: str | None = None


@dataclass(frozen=True, slots=True)
class AcquirePublicationRequest:
    asset: PublicationAsset
    issue_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessingCheckpoint:
    asset: SourceAssetIdentity
    original_identity: ByteIdentity
    processing_signature: ByteIdentity
    result_identity: ByteIdentity | None = None


@dataclass(frozen=True, slots=True)
class DestinationObservation:
    destination_id: str
    confirmed_identity: ByteIdentity | None = None


@dataclass(frozen=True, slots=True)
class AssessUpdatesRequest:
    original: IdentifiedOriginal
    processing_signature: ByteIdentity
    checkpoint: ProcessingCheckpoint | None = None
    target: str = "original"
    destinations: tuple[DestinationObservation, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicationUpdatePlan:
    source_state: str
    processing_required: bool
    destination_actions: tuple[tuple[str, str], ...]
    original_identity: ByteIdentity
    checkpoint_candidate: ProcessingCheckpoint
