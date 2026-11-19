"""Publication identity and source-level evidence, without statistical semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal

from stratbox.core.network import RetryPolicy
from stratbox.core.operations.source.originals import OriginalDestination, StoredOriginal
from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

Format = Literal["pdf", "xlsx", "zip", "rar"]
Qualification = Literal["qualified", "ambiguous"]
Coverage = Literal["complete", "partial", "unknown"]


@dataclass(frozen=True, slots=True)
class RosstatSourceSpec:
    series_id: str
    title: str
    landing_url: str
    discovery_profile_id: str
    accepted_formats: frozenset[str]
    frequency_hint: str
    catalog_version: int = 1

    def __post_init__(self):
        if not self.series_id.startswith("rosstat.") or not self.title or self.catalog_version < 1:
            raise ValueError("rosstat.catalog_invalid")
        if not self.accepted_formats or not self.accepted_formats <= {"pdf", "xlsx", "zip", "rar"}:
            raise ValueError("rosstat.catalog_formats_invalid")


@dataclass(frozen=True, slots=True)
class IssueKey:
    series_id: str
    issue_id: str
    qualification: Literal["publisher_link", "manual_asserted"] = "publisher_link"

    def __post_init__(self):
        if not self.series_id.startswith("rosstat.") or not self.issue_id or len(self.issue_id) > 80:
            raise ValueError("rosstat.issue_invalid")


@dataclass(frozen=True, slots=True)
class AssetKey:
    issue: IssueKey
    asset_id: str

    def __post_init__(self):
        if not self.asset_id or len(self.asset_id) > 80:
            raise ValueError("rosstat.asset_invalid")

    @property
    def source_id(self) -> str:
        digest = sha256(canonical_manifest_bytes({
            "series_id": self.issue.series_id,
            "issue_id": self.issue.issue_id,
            "asset_id": self.asset_id,
        })).hexdigest()
        return "rosstat." + digest


@dataclass(frozen=True, slots=True)
class DiscoveredAsset:
    key: AssetKey | None
    asset_role: str
    url: str
    filename: str
    label_literal: str
    raw_href: str
    declared_format: str
    landing_url: str
    index_identity: ByteIdentity
    profile_version: str
    position: int
    qualification: Qualification

    @property
    def series_id(self) -> str:
        if self.key is not None:
            return self.key.issue.series_id
        return ""

    @property
    def source_id(self) -> str | None:
        return self.key.source_id if self.key is not None else None


@dataclass(frozen=True, slots=True)
class RosstatPublicationIndex:
    series_id: str
    landing_url: str
    index_identity: ByteIdentity
    profile_version: str
    qualified_assets: tuple[DiscoveredAsset, ...]
    ambiguous_assets: tuple[DiscoveredAsset, ...]
    unclassified_count: int
    coverage: Coverage
    # Real page layouts and final attachment destinations require live calibration.
    live_profile_verified: bool = False


@dataclass(frozen=True, slots=True)
class DiscoverRosstatRequest:
    series_id: str
    index: SourcePayload | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class AcquireRosstatRequest:
    asset: DiscoveredAsset
    max_bytes: int = 100 * 1024 * 1024
    deadline_seconds: float = 120
    retry: RetryPolicy = RetryPolicy()


@dataclass(frozen=True, slots=True)
class AcquireRosstatToStoreRequest:
    asset: DiscoveredAsset
    destination: OriginalDestination
    max_bytes: int = 100 * 1024 * 1024
    deadline_seconds: float = 120
    retry: RetryPolicy = RetryPolicy()
    baseline: StoredOriginal | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class AcquiredRosstatAsset:
    asset: DiscoveredAsset
    source: AcquiredSource
    detected_format: Format


@dataclass(frozen=True, slots=True)
class StoredRosstatAsset:
    asset: DiscoveredAsset
    source: StoredOriginal
    detected_format: Format


@dataclass(frozen=True, slots=True)
class PublicationIndexDelta:
    state: Literal["unchanged", "changed", "indeterminate"]
    added_asset_ids: tuple[str, ...]
    missing_asset_ids: tuple[str, ...]
    relocated_asset_ids: tuple[str, ...]
    reason: str
