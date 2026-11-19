"""Separate recognition from publication scope completeness and profile admission."""

from __future__ import annotations

from hashlib import sha256

from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.shared.source_publications import QualifiedInventory
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
    owner_evidence_ref: str, issue_lower_bound: str | None = None,
    issue_upper_bound: str | None = None,
) -> QualifiedInventory:
    """A future verified profile may yield an owner-attested absence baseline.

    A provisional synthetic/online index cannot pass this gate. Authority still
    needs to verify the durable publication state and the owner evidence reference.
    """
    if (
        (index.assessment.scope.scope_id != "full_series"
         and issue_lower_bound is None and issue_upper_bound is None)
        or index.coverage != "complete" or not index.live_profile_verified
        or index.acquisition is None or index.observed_at_utc is None
    ):
        raise ValueError("rosstat.inventory_not_verified")
    return QualifiedInventory(
        index.series_id, index.assessment.scope.scope_id,
        index.assessment.profile_id, index.assessment.profile_version,
        index.observed_at_utc, index.index_identity,
        tuple(item.key.identity for item in index.qualified_assets),
        owner_evidence_ref, issue_lower_bound, issue_upper_bound,
    )
