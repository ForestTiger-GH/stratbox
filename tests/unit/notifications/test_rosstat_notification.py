"""Owner-confirmed version events: coherence, backfill and notification admission."""

from dataclasses import replace
from datetime import datetime, timezone
import pytest

from stratbox.core.notifications.topics import build_catalog
from stratbox.core.observability import (
    fact_from_original_version_commit, fact_from_original_bytes_changed,
    record_from_fact,
)
from stratbox.core.observability.records.event_schemas import SOURCE_ORIGINAL_COMMITTED
from stratbox.core.operations.source.version_comparison import (
    OriginalVersion, CompareOriginalVersionsRequest, compare_original_versions,
)
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import PublicationReceipt
from stratbox.shared.source_publications import (
    SourceAssetIdentity, ConfirmedOriginalPublication, PublishedArtifactRef,
)


def _asset():
    return SourceAssetIdentity("rosstat.short_term_indicators", "2026-08", "main_workbook")


def _transition(old: bytes | None, new: bytes):
    key = _asset()
    candidate = OriginalVersion(key.source_id, ByteIdentity.of(new))
    if old is None:
        request = CompareOriginalVersionsRequest(candidate, "initial")
    else:
        baseline = OriginalVersion(key.source_id, ByteIdentity.of(old), "f" * 64)
        request = CompareOriginalVersionsRequest(candidate, "available", baseline)
    result = compare_original_versions(request)
    assert result.outcome == "succeeded"
    return result.value


def _publication(change, *, confirmed=True, source_id=None, identity=None):
    identity = identity or change.new_identity
    receipt = PublicationReceipt(
        "tabularium", "originals", source_id or change.source_id,
        change.transition_id, identity,
        "confirmed" if confirmed else "unknown",
    )
    ref = PublishedArtifactRef(
        "originals", change.source_id, identity.sha256, identity, "owner-verified-commit",
    )
    if confirmed:
        return ConfirmedOriginalPublication(receipt, ref)
    return receipt


def _fact(change, publication=None, *, mode="live", asset=None):
    return fact_from_original_version_commit(
        change, publication or _publication(change), asset=asset or _asset(),
        mode=mode, occurred_at_utc=datetime.now(timezone.utc),
    )


def test_owner_unknown_and_artifact_mismatch_rejected():
    change = _transition(None, b"A")
    with pytest.raises(ValueError):
        _fact(change, _publication(change, confirmed=False))
    wrong = ByteIdentity.of(b"wrong")
    with pytest.raises(ValueError):
        _fact(change, _publication(change, identity=wrong))
    with pytest.raises(ValueError):
        _fact(change, _publication(change, source_id="rosstat.different"))


def test_wrong_series_issue_asset_rejected_even_if_sha_is_valid():
    change = _transition(None, b"A")
    wrong = SourceAssetIdentity("rosstat.population_municipalities", "2026", "population_workbook")
    with pytest.raises(ValueError, match="original.commit_unqualified"):
        _fact(change, asset=wrong)


def test_event_schema_and_notification_predicate_are_coherent():
    topic = next(x for x in build_catalog().definitions()
                 if x.topic_id == "source.original_version_committed")
    for old, new, expected, eligible in (
        (None, b"A", "first_seen", False),
        (b"A", b"B", "revised", True),
    ):
        change = _transition(old, new)
        fact = _fact(change)
        record = record_from_fact(fact)
        assert record.payload["change"] == expected
        assert record.payload["artifact_ref"]["sha256"] == change.new_identity.sha256
        data = SOURCE_ORIGINAL_COMMITTED.validate(record)
        assert topic.eligible(record, data) is eligible


def test_published_artifact_tampering_rejected_at_topic_boundary():
    change = _transition(b"A", b"B")
    record = record_from_fact(_fact(change))
    topic = next(x for x in build_catalog().definitions()
                 if x.topic_id == "source.original_version_committed")
    forged = replace(record, payload={
        **record.payload, "series_id": "rosstat.population_municipalities",
    })
    data = SOURCE_ORIGINAL_COMMITTED.validate(forged)
    with pytest.raises(ValueError, match="journal.original_asset_identity_mismatch"):
        topic.eligible(forged, data)
    bad_artifact = replace(record, payload={
        **record.payload, "artifact_ref": {
            **record.payload["artifact_ref"], "sha256": "f" * 64,
        },
    })
    with pytest.raises(ValueError, match="journal.original_artifact_mismatch"):
        topic.eligible(bad_artifact, SOURCE_ORIGINAL_COMMITTED.validate(bad_artifact))


def test_old_byte_change_helper_forbids_backfill():
    change = _transition(b"A", b"B")
    with pytest.raises(ValueError, match="original.prior_version_required"):
        fact_from_original_bytes_changed(
            change, _publication(change), asset=_asset(), mode="backfill",
            occurred_at_utc=datetime.now(timezone.utc),
        )
    fact = fact_from_original_bytes_changed(
        change, _publication(change), asset=_asset(), mode="live",
        occurred_at_utc=datetime.now(timezone.utc),
    )
    assert record_from_fact(fact).kind == "source.bytes_changed"


def test_backfill_requires_explicit_opt_in():
    topic = next(x for x in build_catalog().definitions()
                 if x.topic_id == "source.original_version_committed")
    assert topic.explicit_opt_in == ("mode", "backfill")
    change = _transition(b"A", b"B")
    record = record_from_fact(_fact(change, mode="backfill"))
    assert topic.eligible(record, SOURCE_ORIGINAL_COMMITTED.validate(record))
