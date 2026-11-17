from dataclasses import replace
from datetime import timedelta

import pytest

from stratbox.execution import OperationFailure
from stratbox.notifications import (
    FilterCondition, InspectRequest, PrepareRequest, SubscriptionChange, accessible_topics, amend_checkpoint,
    configure_subscription, flush_audit, inspect, prepare, register_replay,
)
from stratbox.base.filestore import LocalFileStore
from stratbox.observability import (
    DomainFact, FileJournalReader, FileJournalWriter, JournalReadLimits, ObjectRef,
    PersistencePolicy, SegmentDescriptor, record_from_fact,
)

from conftest import TIME, byte_event


def test_read_only_preview_live_cut_and_replay_share_dispatch_identity(session):
    runtime, key, context, source, _, _ = session
    source.records.extend([byte_event(), byte_event(observation="obs-2")])
    report = inspect(InspectRequest(key), reader=runtime, context=context)
    assert (report.report.prepared, report.report.duplicate) == (1, 1)
    assert runtime.state.get_checkpoint(key).last_offset == 0
    first = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert first.outcome == "succeeded", first.diagnostics
    assert (first.value.prepared, first.value.duplicate) == (1, 1)
    replay_key = replace(key, replay_id="again")
    register_replay(replay_key, 1, 2, TIME + timedelta(days=1), runtime=runtime, context=context)
    replay = prepare(PrepareRequest(replay_key, mode="replay"), runtime=runtime, context=context)
    assert replay.value.duplicate == 2
    assert replay.value.prepared == 0
    assert runtime.state.get_checkpoint(key).last_offset == 2


def test_unsupported_schema_blocks_only_noncommitted_suffix_and_can_be_waived(session):
    runtime, key, context, source, _, _ = session
    source.records.extend((byte_event(), byte_event("e2", "obs-2", version=2), byte_event("e3", "obs-3")))
    first = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert first.outcome == "partial", first.diagnostics
    assert (first.value.checkpoint.last_offset, first.value.blocked_at) == (1, 2)
    assert first.value.reason_code == "journal.unsupported_data_schema"
    new = amend_checkpoint(key, expected=first.value.checkpoint, head_ref="head-3", last_offset=2,
                           action="waive", reason_code="unsupported_edition", evidence_ref="case-1",
                           runtime=runtime, context=context)
    assert new.last_offset == 2
    next_page = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert next_page.value.prepared == 1
    assert next_page.value.caught_up


def test_same_observation_changed_bytes_are_conflict_across_pages(session):
    runtime, key, context, source, _, _ = session
    source.records.append(byte_event())
    assert prepare(PrepareRequest(key), runtime=runtime, context=context).value.prepared == 1
    source.records.append(byte_event(new="c"))
    seen = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert seen.value.reason_code == "journal.record_identity_conflict"
    assert seen.value.checkpoint.last_offset == 1


def test_conflicting_semantic_value_for_same_transition_blocks(session):
    runtime, key, context, source, _, _ = session
    source.records.extend((byte_event(), byte_event(observation="obs-2", new="c")))
    seen = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert seen.value.reason_code == "notification.fact_identity_conflict"
    assert seen.value.prepared == 1


def test_catch_up_budget_and_service_record_filter(session):
    runtime, key, context, source, _, _ = session
    source.records.append(record_from_fact(DomainFact(
        "notification.prepared", ObjectRef("notification", "x"), "audit", TIME,
    )))
    source.records.extend((byte_event("e1", "obs-1"), byte_event("e2", "obs-2")))
    req = PrepareRequest(key, JournalReadLimits(max_positions=1), "catch_up", max_pages=3)
    result = prepare(req, runtime=runtime, context=context)
    assert result.value.examined == 3
    assert result.value.prepared == 2
    assert result.value.caught_up


def test_activation_and_revision_rules(session):
    runtime, key, context, source, _, spec = session
    configure_subscription(SubscriptionChange("disable", spec, 2), runtime=runtime, context=context)
    source.records.append(byte_event())
    configure_subscription(SubscriptionChange("enable", spec, 3), runtime=runtime, context=context)
    assert runtime.state.get_checkpoint(key).last_offset == 1
    edited = replace(spec, filters=(FilterCondition("source_id", "eq", ("different",)),))
    configure_subscription(SubscriptionChange("update", edited, 4), runtime=runtime, context=context)
    source.records.append(byte_event("e2", "obs-2"))
    result = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert result.value.skipped == 1
    assert result.value.checkpoint.last_offset == 2
    with pytest.raises(OperationFailure, match="subscription.revision_conflict"):
        configure_subscription(SubscriptionChange("update", edited, 4), runtime=runtime, context=context)


def test_filter_unknown_field_and_denied_fields_are_rejected_before_match(session):
    runtime, key, context, source, _, spec = session
    changed = replace(spec, filters=(FilterCondition("route_id", "eq", ("updates",)),))
    with pytest.raises(OperationFailure, match="subscription.filter_invalid"):
        configure_subscription(SubscriptionChange("update", changed, 2), runtime=runtime, context=context)
    scoped = replace(spec, filters=(FilterCondition("source_id", "eq", ("official",)),))
    configure_subscription(SubscriptionChange("update", scoped, 2), runtime=runtime, context=context)
    runtime.authority.fields -= {"source_id"}
    source.records.append(byte_event())
    result = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert result.value.reasons == (("notification.access_denied", 1),)
    assert result.value.matched == 0


def test_temporary_authority_failure_keeps_position(session):
    runtime, key, context, source, _, _ = session
    source.records.append(byte_event())
    runtime.authority.unavailable_actions.add("prepare")
    result = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert result.outcome == "unknown"
    assert runtime.state.get_checkpoint(key).last_offset == 0


@pytest.mark.parametrize("format", ("json", "jsonl"))
def test_audit_is_exported_once_after_segment_confirmation(session, tmp_path, format):
    runtime, key, context, source, _, _ = session
    source.records.append(byte_event())
    prepare(PrepareRequest(key), runtime=runtime, context=context)
    store = LocalFileStore(tmp_path)
    writer = FileJournalWriter(store, "audit", writer_id="notifications", policy=PersistencePolicy(format=format))
    receipt = flush_audit(runtime.state, key.scope_id, writer)
    assert receipt.state == "confirmed"
    stored = FileJournalReader(store, namespace=writer.namespace).read_verified_segment(
        SegmentDescriptor.from_receipt(receipt),
    )
    assert tuple(record.kind for record in stored) == (
        "subscription.created", "subscription.activated", "notification.page_processed", "notification.prepared",
    )
    assert stored[-1].cause_record_ids == (source.records[0].record_id,)
    assert flush_audit(runtime.state, key.scope_id, writer) is None


def test_discovery_exposes_only_permitted_topic_projections(session):
    runtime, _, context, _, _, spec = session
    entries = accessible_topics(spec, reader=runtime, context=context)
    assert {row.topic_id for row in entries} == {"source.bytes_changed", "publication.committed"}
    runtime.authority.fields -= {"old_sha256"}
    entries = accessible_topics(spec, reader=runtime, context=context)
    assert {row.topic_id for row in entries} == {"publication.committed"}
