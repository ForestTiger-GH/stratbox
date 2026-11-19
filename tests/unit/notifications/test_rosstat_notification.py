"""An owner-confirmed original is eligible for structured notification."""

from datetime import datetime, timezone
import pytest

from stratbox.core.notifications.topics import build_catalog
from stratbox.core.observability import (
    fact_from_original_version_commit, fact_from_original_bytes_changed, record_from_fact,
)
from stratbox.core.observability.records.field_policy import validate_builtin_fields
from stratbox.core.operations.source.version_comparison import (
    OriginalVersion, CompareOriginalVersionsRequest, compare_original_versions,
)
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import PublicationReceipt


def _transition(old, new):
    candidate = OriginalVersion("rosstat.asset", ByteIdentity.of(new))
    if old is None:
        request = CompareOriginalVersionsRequest(candidate, "confirmed_absent")
    else:
        before = OriginalVersion(candidate.source_id, ByteIdentity.of(old))
        request = CompareOriginalVersionsRequest(candidate, "available", before)
    result = compare_original_versions(request)
    assert result.outcome == "succeeded"
    return result.value


def _receipt(comparison, confirmation="confirmed"):
    return PublicationReceipt(
        "tabularium", "source_archive", comparison.source_id,
        comparison.transition_id, comparison.new_identity, confirmation,
    )


def test_owner_confirmation_is_required():
    change = _transition(None, b"first")
    with pytest.raises(ValueError):
        fact_from_original_version_commit(
            change, _receipt(change, "unknown"), series_id="rosstat.test",
            issue_id="2026-08", asset_id="primary",
            mode="live", occurred_at_utc=datetime.now(timezone.utc),
        )


def test_first_seen_and_revised_events_have_correct_schema():
    catalog = build_catalog()
    assert "source.original_version_committed" in {x.topic_id for x in catalog.definitions()}
    topic = next(t for t in catalog.definitions() if t.topic_id == "source.original_version_committed")
    onboarding = _transition(None, b"baseline")
    onboarding_fact = fact_from_original_version_commit(
        onboarding, _receipt(onboarding), series_id="rosstat.test",
        issue_id="2026-08", asset_id="primary", mode="live",
        occurred_at_utc=datetime.now(timezone.utc),
    )
    from stratbox.core.observability.records.event_schemas import SOURCE_ORIGINAL_COMMITTED
    rec = record_from_fact(onboarding_fact)
    assert not topic.eligible(rec, SOURCE_ORIGINAL_COMMITTED.validate(rec))
    for old, new, state in ((None, b"first", "first_seen"), (b"first", b"second", "revised")):
        change = _transition(old, new)
        assert change.state == state
        fact = fact_from_original_version_commit(
            change, _receipt(change), series_id="rosstat.test",
            issue_id="2026-08", asset_id="primary",
            mode="live", occurred_at_utc=datetime.now(timezone.utc),
        )
        record = record_from_fact(fact)
        validate_builtin_fields(record)
        assert record.payload["transition_id"] == change.transition_id
        assert record.kind == "source.original_version_committed"
        if old is not None:
            original_change = fact_from_original_bytes_changed(
                change, _receipt(change), occurred_at_utc=datetime.now(timezone.utc),
            )
            assert record_from_fact(original_change).kind == "source.bytes_changed"
