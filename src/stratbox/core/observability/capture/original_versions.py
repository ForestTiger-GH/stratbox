"""Facts about owner-confirmed raw source versions (not economic observations)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from stratbox.core.execution import Correlation
from stratbox.core.observability.records.contracts import DomainFact, ObjectRef, make_fact_id, require_utc
from stratbox.core.operations.source.version_comparison import OriginalVersionComparison
from stratbox.shared.evidence import PublicationReceipt

Mode = Literal["live", "backfill"]


def _qualified(
    comparison: OriginalVersionComparison, receipt: PublicationReceipt,
) -> None:
    if (
        comparison.state not in {"first_seen", "new_release", "revised"}
        or comparison.transition_id is None
        or receipt.confirmation != "confirmed"
        or receipt.transition_id != comparison.transition_id
        or receipt.release_id != comparison.source_id
        or receipt.identity != comparison.new_identity
    ):
        raise ValueError("original.commit_unqualified")


def fact_from_original_version_commit(
    comparison: OriginalVersionComparison, publication: PublicationReceipt, *,
    series_id: str, issue_id: str, asset_id: str,
    mode: Mode, occurred_at_utc: datetime,
    correlation: Correlation | None = None,
) -> DomainFact:
    """Accept only an independently confirmed owner publication receipt."""
    _qualified(comparison, publication)
    if mode not in {"live", "backfill"}:
        raise ValueError("original.publication_mode_invalid")
    subject = ObjectRef("source", comparison.source_id, identity=comparison.new_identity)
    payload = {
        "data_version": 1,
        "source_id": comparison.source_id,
        "series_id": series_id, "issue_id": issue_id, "asset_id": asset_id,
        "transition_id": comparison.transition_id, "change": comparison.state,
        "previous_sha256": comparison.old_identity.sha256 if comparison.old_identity else None,
        "current_sha256": comparison.new_identity.sha256,
        "size_bytes": comparison.new_identity.size,
        "mode": mode, "owner_id": publication.owner_id,
        "destination_id": publication.destination_id,
    }
    return DomainFact(
        "source.original_version_committed", subject,
        make_fact_id("source.original_version_committed", subject, {
            "transition_id": comparison.transition_id,
            "owner_id": publication.owner_id, "destination_id": publication.destination_id,
        }),
        require_utc(occurred_at_utc), payload,
        references=(ObjectRef("publication", publication.release_id, "owner_confirmed"),),
        correlation=correlation or Correlation(),
    )


def fact_from_original_bytes_changed(
    comparison: OriginalVersionComparison, publication: PublicationReceipt, *,
    occurred_at_utc: datetime, correlation: Correlation | None = None,
) -> DomainFact:
    """Existing topic, applicable only to a qualified prior SHA -> new SHA transition."""
    _qualified(comparison, publication)
    if comparison.state != "revised" or comparison.old_identity is None:
        raise ValueError("original.prior_version_required")
    subject = ObjectRef("source", comparison.source_id, identity=comparison.new_identity)
    payload = {
        "data_version": 1,
        "source_id": comparison.source_id,
        "transition_id": comparison.transition_id,
        "old_sha256": comparison.old_identity.sha256,
        "new_sha256": comparison.new_identity.sha256,
        "size_bytes": comparison.new_identity.size,
        "time_basis": "observed_change",
    }
    return DomainFact(
        "source.bytes_changed", subject,
        make_fact_id("source.bytes_changed", subject, {
            "transition_id": comparison.transition_id, "owner_id": publication.owner_id,
        }),
        require_utc(occurred_at_utc), payload,
        correlation=correlation or Correlation(),
    )
