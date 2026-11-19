"""Publisher issue and source-asset identity, separate from statistical observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from stratbox.core.network import RetryPolicy
from stratbox.core.operations.source.originals import OriginalDestination, StoredOriginal
from stratbox.shared.evidence import AcquiredSource, AcquisitionReceipt, SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import SourceAssetIdentity

Format = Literal["pdf", "xlsx", "zip", "rar"]
Qualification = Literal["qualified", "ambiguous"]
Coverage = Literal["complete", "partial", "unknown"]
AssessmentStatus = Literal["verified_complete", "verified_partial", "unverified"]


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
        if not isinstance(self.issue, IssueKey) or not self.asset_id or len(self.asset_id) > 80:
            raise ValueError("rosstat.asset_invalid")
        SourceAssetIdentity(self.issue.series_id, self.issue.issue_id, self.asset_id)

    @property
    def identity(self) -> SourceAssetIdentity:
        return SourceAssetIdentity(self.issue.series_id, self.issue.issue_id, self.asset_id)

    @property
    def source_id(self) -> str:
        return self.identity.source_id


@dataclass(frozen=True, slots=True)
class IndexScope:
    series_id: str
    scope_id: str
    covered_sections: tuple[str, ...] = ()
    issue_lower_bound: str | None = None
    issue_upper_bound: str | None = None

    def __post_init__(self):
        if not self.series_id.startswith("rosstat.") or not self.scope_id:
            raise ValueError("rosstat.scope_invalid")
        if len(self.covered_sections) > 128 or len(set(self.covered_sections)) != len(self.covered_sections):
            raise ValueError("rosstat.scope_sections_invalid")


@dataclass(frozen=True, slots=True)
class DiscoveryAssessment:
    status: AssessmentStatus
    profile_id: str
    profile_version: str
    scope: IndexScope
    layout_identity: str
    recognized_count: int
    unresolved_count: int
    reason_codes: tuple[str, ...] = ()
    expected_sections: tuple[str, ...] = ()
    # No profile is approved until live publisher HTML calibrates its scope.
    admission_evidence_ref: str | None = None

    def __post_init__(self):
        if self.status not in {"verified_complete", "verified_partial", "unverified"}:
            raise ValueError("rosstat.assessment_invalid")
        if self.recognized_count < 0 or self.unresolved_count < 0 or len(self.reason_codes) > 32:
            raise ValueError("rosstat.assessment_invalid")
        if self.status.startswith("verified") and self.admission_evidence_ref is None:
            raise ValueError("rosstat.assessment_proof_required")
        if self.status == "verified_complete" and (
            self.unresolved_count or not self.expected_sections or not self.scope.covered_sections
            or set(self.expected_sections) != set(self.scope.covered_sections)
        ):
            raise ValueError("rosstat.assessment_not_complete")

    @property
    def coverage(self) -> Coverage:
        return {
            "verified_complete": "complete", "verified_partial": "partial",
            "unverified": "unknown",
        }[self.status]


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
    issue_label: str | None = None
    issue_period_hint: str | None = None
    issue_evidence: str | None = None
    publisher_publication_date: str | None = None
    diagnostic_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if self.qualification == "qualified" and self.key is None:
            raise ValueError("rosstat.asset_unqualified")
        if self.position < 0 or not isinstance(self.index_identity, ByteIdentity):
            raise ValueError("rosstat.asset_invalid")

    @property
    def series_id(self) -> str:
        return self.key.issue.series_id if self.key is not None else ""

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
    assessment: DiscoveryAssessment
    acquisition: AcquisitionReceipt | None = None
    source_kind: Literal["publisher_http", "supplied_payload"] = "supplied_payload"

    def __post_init__(self):
        if self.assessment.scope.series_id != self.series_id:
            raise ValueError("rosstat.index_scope_mismatch")
        if self.assessment.profile_version != self.profile_version:
            raise ValueError("rosstat.index_profile_mismatch")
        if self.acquisition is not None and (
            self.acquisition.identity != self.index_identity
            or self.acquisition.source_id != self.series_id + ".index"
            or self.source_kind != "publisher_http"
        ):
            raise ValueError("rosstat.index_acquisition_invalid")
        if self.source_kind == "publisher_http" and self.acquisition is None:
            raise ValueError("rosstat.index_acquisition_missing")
        if self.assessment.status == "verified_complete" and self.source_kind != "publisher_http":
            raise ValueError("rosstat.index_offline_unverified")

    @property
    def coverage(self) -> Coverage:
        return self.assessment.coverage

    @property
    def live_profile_verified(self) -> bool:
        return self.assessment.status.startswith("verified")

    @property
    def observed_at_utc(self) -> datetime | None:
        return self.acquisition.observed_at_utc if self.acquisition else None


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
    # Advisory discoveries are not proof of complete inventory.
    observed_candidate_ids: tuple[str, ...] = ()
