"""Explicit review of one publisher index; never automatic from found links.

This is an owner attestation about a concrete publisher-acquired document.
It does not prove a website's layout cryptographically; external source review,
authority admission, and durable recording are required of the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stratbox.shared.identity import ByteIdentity
from ..contracts import DiscoveryAssessment, IndexScope, RosstatPublicationIndex


@dataclass(frozen=True, slots=True)
class ReviewedIndexScope:
    """Reviewer-confirmed scope and all asset keys present in exact HTML bytes."""
    series_id: str
    profile_id: str
    profile_version: str
    index_identity: ByteIdentity
    scope_id: str
    expected_sections: tuple[str, ...]
    observed_asset_ids: tuple[str, ...]
    owner_evidence_ref: str
    issue_lower_bound: str | None = None
    issue_upper_bound: str | None = None
    # Labelled manual evidence, not a global automated layout certification.
    review_basis: str = "human_verified"

    def __post_init__(self):
        if (
            not isinstance(self.index_identity, ByteIdentity)
            or self.review_basis != "human_verified"
            or not self.owner_evidence_ref or not self.scope_id
            or not self.expected_sections
            or (self.scope_id != "full_series" and
                self.issue_lower_bound is None and self.issue_upper_bound is None)
            or (self.issue_lower_bound is not None and self.issue_upper_bound is not None
                and self.issue_lower_bound > self.issue_upper_bound)
            or len(set(self.expected_sections)) != len(self.expected_sections)
            or len(set(self.observed_asset_ids)) != len(self.observed_asset_ids)
        ):
            raise ValueError("rosstat.review_evidence_invalid")


def approve_index(
    index: RosstatPublicationIndex, evidence: ReviewedIndexScope,
) -> RosstatPublicationIndex:
    """A precisely scoped manual review gate.

    Automatic monitoring must use a separately calibrated profile; this
    one-document review is specific to its acquisition/index identity.
    """
    if index.source_kind != "publisher_http" or index.acquisition is None:
        raise ValueError("rosstat.review_publisher_receipt_required")
    if (
        evidence.series_id != index.series_id
        or evidence.profile_id != index.assessment.profile_id
        or evidence.profile_version != index.profile_version
        or evidence.index_identity != index.index_identity
        or index.ambiguous_assets or index.unclassified_count
        or tuple(sorted(evidence.observed_asset_ids))
           != tuple(sorted(item.key.source_id for item in index.qualified_assets))
    ):
        raise ValueError("rosstat.review_evidence_mismatch")
    scope = IndexScope(
        index.series_id, evidence.scope_id, evidence.expected_sections,
        evidence.issue_lower_bound, evidence.issue_upper_bound,
    )
    assessment = replace(
        index.assessment, status="verified_complete", scope=scope,
        expected_sections=evidence.expected_sections,
        admission_evidence_ref=evidence.owner_evidence_ref,
    )
    return replace(index, assessment=assessment)
