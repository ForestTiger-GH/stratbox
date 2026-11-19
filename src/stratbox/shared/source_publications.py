"""Publisher-neutral, qualified logical source and publication version evidence.

Evidence structs are explicit owner attestations, not signatures or remote
storage verification. A caller must validate the publishing authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Literal

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import PublicationReceipt

_TOKEN = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z", re.ASCII)


def _token(value: str) -> str:
    if type(value) is not str or not _TOKEN.fullmatch(value):
        raise ValueError("source.identity_token_invalid")
    return value


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("source.evidence_time_invalid")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class SourceAssetIdentity:
    """Stable series/issue/asset key: URL, label, role and byte hash are excluded."""
    series_id: str
    issue_id: str
    asset_id: str

    def __post_init__(self):
        _token(self.series_id)
        _token(self.issue_id)
        _token(self.asset_id)
        if len(self.series_id.split(".", 1)[0]) > 63:
            raise ValueError("source.publisher_namespace_too_long")

    @property
    def source_id(self) -> str:
        digest = sha256(canonical_manifest_bytes({
            "series_id": self.series_id, "issue_id": self.issue_id,
            "asset_id": self.asset_id,
        })).hexdigest()
        return self.series_id.split(".", 1)[0] + "." + digest


@dataclass(frozen=True, slots=True)
class QualifiedInventory:
    """A named owner attests complete enumeration within its declared scope.

    For a recent rolling listing issue_lower_bound is inclusive. A missing
    upper bound denotes the then-visible current releases, not all future URLs.
    The declaration must come from a verified layout and durable owner state.
    """
    series_id: str
    scope_id: str
    profile_id: str
    profile_version: str
    observed_at_utc: datetime
    index_identity: ByteIdentity
    assets: tuple[SourceAssetIdentity, ...]
    owner_evidence_ref: str
    issue_lower_bound: str | None = None
    issue_upper_bound: str | None = None
    completeness: Literal["verified_complete"] = "verified_complete"

    def __post_init__(self):
        for value in (self.series_id, self.scope_id, self.profile_id,
                      self.profile_version, self.owner_evidence_ref):
            _token(value)
        _utc(self.observed_at_utc)
        if not isinstance(self.index_identity, ByteIdentity):
            raise ValueError("source.inventory_identity_invalid")
        if self.completeness != "verified_complete":
            raise ValueError("source.inventory_not_complete")
        if not isinstance(self.assets, tuple) or any(
            not isinstance(item, SourceAssetIdentity) or item.series_id != self.series_id
            for item in self.assets
        ):
            raise ValueError("source.inventory_assets_invalid")
        if len(self.assets) > 100_000 or len(set(self.assets)) != len(self.assets):
            raise ValueError("source.inventory_assets_invalid")
        if self.issue_lower_bound is not None:
            _token(self.issue_lower_bound)
        if self.issue_upper_bound is not None:
            _token(self.issue_upper_bound)
        if self.issue_lower_bound is not None and self.issue_upper_bound is not None and (
            self.issue_lower_bound > self.issue_upper_bound
        ):
            raise ValueError("source.inventory_scope_invalid")
        if self.scope_id != "full_series" and (
            self.issue_lower_bound is None and self.issue_upper_bound is None
        ):
            raise ValueError("source.inventory_scope_unbounded")

    @property
    def identity(self) -> str:
        return sha256(canonical_manifest_bytes({
            "schema": 1, "series_id": self.series_id, "scope_id": self.scope_id,
            "profile_id": self.profile_id, "profile_version": self.profile_version,
            "observed_at": self.observed_at_utc, "index_sha": self.index_identity.sha256,
            "index_size": self.index_identity.size,
            "assets": sorted(item.source_id for item in self.assets),
            "issue_lower_bound": self.issue_lower_bound,
            "issue_upper_bound": self.issue_upper_bound,
            "owner_evidence_ref": self.owner_evidence_ref,
        })).hexdigest()

    def covers_issue(self, issue_id: str) -> bool:
        return (
            (self.issue_lower_bound is None or issue_id >= self.issue_lower_bound)
            and (self.issue_upper_bound is None or issue_id <= self.issue_upper_bound)
        )


@dataclass(frozen=True, slots=True)
class InventoryAbsenceEvidence:
    """Claim that this exact logical asset is absent from an owner-qualified list."""
    asset: SourceAssetIdentity
    inventory: QualifiedInventory

    def __post_init__(self):
        if not isinstance(self.asset, SourceAssetIdentity) or not isinstance(self.inventory, QualifiedInventory):
            raise ValueError("source.absence_evidence_invalid")
        if (
            self.asset.series_id != self.inventory.series_id
            or not self.inventory.covers_issue(self.asset.issue_id)
            or self.asset in self.inventory.assets
        ):
            raise ValueError("source.absence_unproven")

    @property
    def existing_issue(self) -> bool:
        return any(item.issue_id == self.asset.issue_id for item in self.inventory.assets)


@dataclass(frozen=True, slots=True)
class QualifiedAssetPresenceEvidence:
    """A current, owner-reviewed publisher index explicitly contains this asset.

    Both the current and prior inventories must have matching publisher
    profile/scope definitions before a NEW_RELEASE or NEW_ASSET conclusion.
    """
    asset: SourceAssetIdentity
    series_id: str
    scope_id: str
    profile_id: str
    profile_version: str
    index_identity: ByteIdentity
    observed_at_utc: datetime
    owner_evidence_ref: str
    issue_lower_bound: str | None = None
    issue_upper_bound: str | None = None

    def __post_init__(self):
        if not isinstance(self.asset, SourceAssetIdentity) or self.asset.series_id != self.series_id:
            raise ValueError("source.presence_asset_invalid")
        for value in (self.series_id, self.scope_id, self.profile_id,
                      self.profile_version, self.owner_evidence_ref):
            _token(value)
        if not isinstance(self.index_identity, ByteIdentity):
            raise ValueError("source.presence_index_invalid")
        _utc(self.observed_at_utc)
        if self.issue_lower_bound is not None:
            _token(self.issue_lower_bound)
        if self.issue_upper_bound is not None:
            _token(self.issue_upper_bound)
        if self.scope_id != "full_series" and (
            self.issue_lower_bound is None and self.issue_upper_bound is None
        ):
            raise ValueError("source.presence_scope_unbounded")
        if self.issue_lower_bound is not None and self.asset.issue_id < self.issue_lower_bound:
            raise ValueError("source.presence_out_of_scope")
        if self.issue_upper_bound is not None and self.asset.issue_id > self.issue_upper_bound:
            raise ValueError("source.presence_out_of_scope")


@dataclass(frozen=True, slots=True)
class PublishedArtifactRef:
    """Safe semantic reference to one owner-confirmed, re-readable version."""
    scope_id: str
    artifact_id: str
    version_id: str
    identity: ByteIdentity
    owner_proof_ref: str

    def __post_init__(self):
        for value in (self.scope_id, self.artifact_id,
                      self.version_id, self.owner_proof_ref):
            _token(value)
        if not isinstance(self.identity, ByteIdentity):
            raise ValueError("source.published_identity_invalid")

    @property
    def public_ref(self) -> dict[str, object]:
        return {
            "scope_id": self.scope_id, "artifact_id": self.artifact_id,
            "version_id": self.version_id, "sha256": self.identity.sha256,
            "size_bytes": self.identity.size,
        }


@dataclass(frozen=True, slots=True)
class ConfirmedOriginalPublication:
    """Owner claim: must be backed by independently checked storage/Git evidence."""
    receipt: PublicationReceipt
    artifact: PublishedArtifactRef

    def __post_init__(self):
        if not isinstance(self.receipt, PublicationReceipt) or not isinstance(self.artifact, PublishedArtifactRef):
            raise ValueError("source.publication_receipt_invalid")
        if (
            self.receipt.confirmation != "confirmed"
            or self.receipt.identity != self.artifact.identity
            or self.receipt.destination_id != self.artifact.scope_id
        ):
            raise ValueError("source.publication_unconfirmed")



@dataclass(frozen=True, slots=True)
class ConfirmedSourceVersion:
    """Portable durable cursor for one accepted logical original.

    Consumers persist this together with their own outbox/owner publication
    transaction. The core comparator reads its transition_id as the parent
    chain, independent of whether the physical version lives in Git or a
    content-addressed store.
    """
    asset: SourceAssetIdentity
    artifact: PublishedArtifactRef
    transition_id: str
    published_at_utc: datetime
    previous_transition_id: str | None = None
    index_identity: ByteIdentity | None = None

    def __post_init__(self):
        if not isinstance(self.asset, SourceAssetIdentity) or not isinstance(self.artifact, PublishedArtifactRef):
            raise ValueError("source.version_checkpoint_invalid")
        if not isinstance(self.transition_id, str) or not re.fullmatch(r"[0-9a-f]{64}", self.transition_id):
            raise ValueError("source.version_checkpoint_invalid")
        if self.previous_transition_id is not None and (
            not isinstance(self.previous_transition_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", self.previous_transition_id)
            or self.previous_transition_id == self.transition_id
        ):
            raise ValueError("source.version_checkpoint_invalid")
        if self.index_identity is not None and not isinstance(self.index_identity, ByteIdentity):
            raise ValueError("source.version_checkpoint_invalid")
        _utc(self.published_at_utc)

    @property
    def identity(self) -> ByteIdentity:
        return self.artifact.identity

    @property
    def source_id(self) -> str:
        return self.asset.source_id
