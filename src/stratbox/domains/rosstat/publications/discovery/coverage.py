"""Separate recognition from publication scope completeness and profile admission."""

from __future__ import annotations

from hashlib import sha256

from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.shared.source_publications import QualifiedInventory, QualifiedAssetPresenceEvidence
from ..contracts import DiscoveryAssessment, IndexScope, RosstatPublicationIndex


def assess(
    *,
    series_id: str, profile_id: str, profile_version: str,
    index_sha256: str, qualified: int, unresolved: int,
    reasons: tuple[str, ...] = (),
) -> DiscoveryAssessment:
    """All currently shipped profiles are provisional, including synthetic fixtures.

    The existence of known anchors never proves the publisher's list is complete.
    """
    layout_identity = sha256(canonical_manifest_bytes({
        "profile": profile_id, "version": profile_version,
        "document": index_sha256,
    })).hexdigest()
    if not reasons:
        reasons = ("publisher_layout_not_calibrated",)
    return DiscoveryAssessment(
        "unverified", profile_id, profile_version, IndexScope(series_id, "landing_page"),
        layout_identity, qualified, unresolved, reasons,
    )


def qualified_inventory_from_index(
    index: RosstatPublicationIndex, *,
    owner_evidence_ref: str,
) -> QualifiedInventory:
    """A future verified profile may yield an owner-attested absence baseline.

    A provisional synthetic/online index cannot pass this gate. Authority still
    needs to verify the durable publication state and the owner evidence reference.
    """
    if (
        index.coverage != "complete" or not index.live_profile_verified
        or index.acquisition is None or index.observed_at_utc is None
    ):
        raise ValueError("rosstat.inventory_not_verified")
    return QualifiedInventory(
        index.series_id, index.assessment.scope.scope_id,
        index.assessment.profile_id, index.assessment.profile_version,
        index.observed_at_utc, index.index_identity,
        tuple(item.key.identity for item in index.qualified_assets),
        owner_evidence_ref, index.assessment.scope.issue_lower_bound,
        index.assessment.scope.issue_upper_bound,
    )



def qualified_presence_from_index(
    index: RosstatPublicationIndex, asset_source_id: str, *, owner_evidence_ref: str,
) -> QualifiedAssetPresenceEvidence:
    """Presence admission requires an exactly reviewed current publisher index."""
    if index.coverage != "complete" or not index.live_profile_verified or index.acquisition is None:
        raise ValueError("rosstat.presence_not_verified")
    asset = next(
        (item for item in index.qualified_assets
         if item.key is not None and item.key.source_id == asset_source_id),
        None,
    )
    if asset is None:
        raise ValueError("rosstat.presence_asset_missing")
    scope = index.assessment.scope
    return QualifiedAssetPresenceEvidence(
        asset.key.identity, index.series_id, scope.scope_id,
        index.assessment.profile_id, index.profile_version, index.index_identity,
        index.observed_at_utc, owner_evidence_ref,
        scope.issue_lower_bound, scope.issue_upper_bound,
    )
