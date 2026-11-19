"""Owner-qualified original version facts and closed notification topic."""

from datetime import datetime, timezone

import pytest

from stratbox.core.observability import fact_from_original_version_commit, record_from_fact
from stratbox.core.notifications.topics import build_catalog
from stratbox.core.observability.records.field_policy import FieldSchemaRegistry
from stratbox.core.operations.source.version_comparison import (
    OriginalVersion, CompareOriginalVersionsRequest, compare_original_versions,
)
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import PublicationReceipt


def test_committed_original_topic_rejects_unconfirmed_publication():
    candidate = OriginalVersion("rosstat.original", ByteIdentity.of(b"first"))
    change = compare_original_versions(
        CompareOriginalVersionsRequest(candidate, "confirmed_absent")
    ).value
    assert change.state == "first_seen"
    receipt = PublicationReceipt(
        "tabularium", "source_archive", candidate.source_id,
        change.transition_id, candidate.identity, "unknown",
    )
    with pytest.raises(ValueError):
        fact_from_original_version_commit(
            change, receipt, series_id="rosstat.test", issue_id="2026-08",
            asset_id="primary", mode="live", occurred_at_utc=datetime.now(timezone.utc),
        )
    receipt = PublicationReceipt(
        receipt.owner_id, receipt.destination_id, receipt.release_id,
        receipt.transition_id, receipt.identity, "confirmed",
    )
    fact = fact_from_original_version_commit(
        change, receipt, series_id="rosstat.test", issue_id="2026-08",
        asset_id="primary", mode="live", occurred_at_utc=datetime.now(timezone.utc),
    )
    record = record_from_fact(fact)
    catalog = build_catalog()
    names = {item.topic_id for item in catalog.definitions()}
    assert "source.original_version_committed" in names
    assert record.kind == "source.original_version_committed"
