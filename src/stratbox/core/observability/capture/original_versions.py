"""Source-neutral events for owner-confirmed exact original versions.

A publication receipt is an authority-owned assertion; a core fact helper
checks internal consistency, not a remote Git push. Consumers must verify
their provider evidence before issuing ConfirmedOriginalPublication.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from stratbox.core.execution import Correlation
from stratbox.core.observability.records.contracts import DomainFact, ObjectRef, make_fact_id, require_utc
from stratbox.core.operations.source.version_comparison import OriginalVersionComparison
from stratbox.shared.source_publications import ConfirmedOriginalPublication, SourceAssetIdentity

Mode = Literal["live", "backfill"]
_CHANGED = frozenset({"first_seen", "new_release", "new_asset", "revised"})


def _qualified(
    comparison: OriginalVersionComparison, publication: ConfirmedOriginalPublication,
    asset: SourceAssetIdentity,
) -> None:
    if not isinstance(asset, SourceAssetIdentity) or not isinstance(publication, ConfirmedOriginalPublication):
        raise ValueError("original.publication_evidence_required")
    receipt, artifact = publication.receipt, publication.artifact
    if (
        comparison.state not in _CHANGED
        or comparison.transition_id is None
        or comparison.source_id != asset.source_id
        or receipt.confirmation != "confirmed"
        or receipt.transition_id != comparison.transition_id
        or receipt.release_id != asset.source_id
        or receipt.identity != comparison.new_identity
        or artifact.identity != comparison.new_identity
        or receipt.destination_id != artifact.scope_id
        or (comparison.state == "revised") != (comparison.old_identity is not None)
    ):
        raise ValueError("original.commit_unqualified")


def fact_from_original_version_commit(
    comparison: OriginalVersionComparison, publication: ConfirmedOriginalPublication, *,
    asset: SourceAssetIdentity, mode: Mode, occurred_at_utc: datetime,
    correlation: Correlation | None = None,
) -> DomainFact:
    """Version fact, with the asset triple and confirmed artifact tied to source_id."""
    _qualified(comparison, publication, asset)
    if mode not in {"live", "backfill"}:
        raise ValueError("original.publication_mode_invalid")
    receipt, artifact = publication.receipt, publication.artifact
    subject = ObjectRef("source", comparison.source_id, identity=comparison.new_identity)
    payload = {
        "data_version": 1, "source_id": asset.source_id,
        "series_id": asset.series_id, "issue_id": asset.issue_id,
        "asset_id": asset.asset_id,
        "transition_id": comparison.transition_id, "change": comparison.state,
        "previous_sha256": comparison.old_identity.sha256 if comparison.old_identity else None,
        "previous_transition_id": comparison.previous_transition_id,
        "current_sha256": comparison.new_identity.sha256,
        "size_bytes": comparison.new_identity.size,
        "mode": mode, "owner_id": receipt.owner_id,
        "destination_id": receipt.destination_id,
        "artifact_ref": artifact.public_ref,
        "publication_proof_ref": artifact.owner_proof_ref,
    }
    return DomainFact(
        "source.original_version_committed", subject,
        make_fact_id("source.original_version_committed", subject, {
            "transition_id": comparison.transition_id, "owner_id": receipt.owner_id,
            "destination_id": receipt.destination_id,
            "artifact_version_id": artifact.version_id,
            "publication_proof_ref": artifact.owner_proof_ref,
        }),
        require_utc(occurred_at_utc), payload,
        references=(ObjectRef("publication", receipt.release_id, "owner_confirmed"),),
        correlation=correlation or Correlation(),
    )


def fact_from_original_bytes_changed(
    comparison: OriginalVersionComparison, publication: ConfirmedOriginalPublication, *,
    asset: SourceAssetIdentity, mode: Mode, occurred_at_utc: datetime,
    correlation: Correlation | None = None,
) -> DomainFact:
    """Legacy topic for explicitly live revisions only; backfills stay silent."""
    _qualified(comparison, publication, asset)
    if mode != "live" or comparison.state != "revised" or comparison.old_identity is None:
        raise ValueError("original.prior_version_required")
    subject = ObjectRef("source", comparison.source_id, identity=comparison.new_identity)
    payload = {
        "data_version": 1, "source_id": comparison.source_id,
        "transition_id": comparison.transition_id,
        "old_sha256": comparison.old_identity.sha256,
        "new_sha256": comparison.new_identity.sha256,
        "size_bytes": comparison.new_identity.size,
        "time_basis": "observed_change",
    }
    return DomainFact(
        "source.bytes_changed", subject,
        make_fact_id("source.bytes_changed", subject, {
            "transition_id": comparison.transition_id,
            "owner_id": publication.receipt.owner_id,
        }),
        require_utc(occurred_at_utc), payload,
        correlation=correlation or Correlation(),
    )
