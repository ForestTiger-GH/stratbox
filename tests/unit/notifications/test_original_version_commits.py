"""Publisher-neutral asset-bound and owner-bound facts must be well-typed."""

from datetime import datetime, timezone
import pytest

from stratbox.core.observability import fact_from_original_version_commit, record_from_fact
from stratbox.core.notifications.topics import build_catalog
from stratbox.core.operations.source.version_comparison import (
    OriginalVersion, CompareOriginalVersionsRequest, compare_original_versions,
)
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import PublicationReceipt
from stratbox.shared.source_publications import (
    SourceAssetIdentity, ConfirmedOriginalPublication, PublishedArtifactRef,
)


def test_confirmed_original_requires_a_consistent_artifact_reference():
    asset = SourceAssetIdentity("rosstat.test", "2026-08", "workbook")
    candidate = OriginalVersion(asset.source_id, ByteIdentity.of(b"first"))
    comparison = compare_original_versions(
        CompareOriginalVersionsRequest(candidate, "initial")
    ).value
    receipt = PublicationReceipt(
        "owner", "storage", asset.source_id,
        comparison.transition_id, candidate.identity, "unknown",
    )
    artifact = PublishedArtifactRef(
        "storage", asset.source_id, candidate.identity.sha256,
        candidate.identity, "owner-ref",
    )
    with pytest.raises(ValueError):
        ConfirmedOriginalPublication(receipt, artifact)
    committed = ConfirmedOriginalPublication(
        PublicationReceipt(
            "owner", "storage", asset.source_id,
            comparison.transition_id, candidate.identity, "confirmed",
        ), artifact,
    )
    fact = fact_from_original_version_commit(
        comparison, committed, asset=asset, mode="live",
        occurred_at_utc=datetime.now(timezone.utc),
    )
    record = record_from_fact(fact)
    assert record.kind == "source.original_version_committed"
    assert record.payload["source_id"] == asset.source_id
    assert record.payload["publication_proof_ref"] == "owner-ref"
    assert "source.original_version_committed" in {
        row.topic_id for row in build_catalog().definitions()
    }
