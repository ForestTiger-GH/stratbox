from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
import json
from threading import Event

import pytest

from stratbox.system.base.filestore import LocalFileStore
from stratbox.shared.data import ByteIdentity
from stratbox.system.execution import ExecutionContext
from stratbox.system.notifications import (
    DeliverRequest, PrepareRequest, QualifyDeliveryRequest, ReconcileDeliveryRequest, SubscriptionChange,
    build_catalog, configure_subscription, deliver, inspect_dispatch, notification_health, prepare, qualify,
    reconcile, register_replay,
)
from stratbox.system.observability import FileJournalWriter, JournalWriteReceipt, RequiredJournalGate

from conftest import Source, byte_event


def _ready(session):
    runtime, key, context, source, _, _ = session
    source.records.append(byte_event())
    outcome = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert outcome.outcome == "succeeded", outcome.diagnostics
    assert outcome.value.prepared == 1
    row, = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=2)
    return DeliverRequest(key.scope_id, row.intent.dispatch_id)


def test_structured_handoff_and_owner_receipt(session):
    runtime, key, context, _, inbox, _ = session
    request = _ready(session)
    result = deliver(request, runtime=runtime, context=context)
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.state == "consumer_accepted"
    envelope = json.loads(inbox.calls[0].intent.envelope_bytes)
    assert envelope["data"]["source_id"] == "official"
    assert envelope["dispatch_id"] == request.dispatch_id
    assert envelope["event_ref"]["kind"] == "source.bytes_changed"
    assert set(result.effects[0].__dataclass_fields__) >= {"effect_id", "state"}
    result_again = deliver(request, runtime=runtime, context=context)
    assert result_again.value.state == "consumer_accepted"
    assert len(inbox.calls) == 1
    health = notification_health(key, reader=runtime, context=context)
    assert dict(health.counts_by_state) == {"consumer_accepted": 1}
    assert health.due == ()
    assert inspect_dispatch(key.scope_id, request.dispatch_id, reader=runtime, context=context).state == "consumer_accepted"


def test_lost_response_is_reconciled_without_second_handoff(session):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)
    inbox.fail_mode = "lost_response"
    first = deliver(request, runtime=runtime, context=context)
    assert (first.outcome, first.value.state) == ("unknown", "unknown")
    assert deliver(request, runtime=runtime, context=context).value.next_action == "reconcile"
    result = reconcile(ReconcileDeliveryRequest(request.scope_id, request.dispatch_id, first.value.attempt_id),
                       runtime=runtime, context=context)
    assert (result.outcome, result.value.state) == ("succeeded", "consumer_accepted")
    assert len(inbox.calls) == 1


def test_unknown_lookup_never_schedules_retry(session):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)
    inbox.fail_mode = "unavailable"
    first = deliver(request, runtime=runtime, context=context)
    recovery = ReconcileDeliveryRequest(request.scope_id, request.dispatch_id, first.value.attempt_id)
    context.clock.advance(9 * 86400)
    result = reconcile(recovery, runtime=runtime, context=context)
    assert (result.outcome, result.value.state) == ("unknown", "unknown")
    assert deliver(request, runtime=runtime, context=context).value.next_action == "reconcile"
    assert len(inbox.calls) == 1


def test_provisional_refusal_waits_for_the_original_attempt(session):
    runtime, key, context, _, inbox, _ = session
    request = _ready(session)
    inbox.fail_mode = "pending_refusal"
    first = deliver(request, runtime=runtime, context=context)
    assert (first.outcome, first.value.state) == ("unknown", "unknown")
    assert first.value.reason_code == "notification.rejection_unconfirmed"
    original, = inbox.calls
    recovery = ReconcileDeliveryRequest(request.scope_id, request.dispatch_id, original.lookup.attempt_id)
    context.clock.advance(3600)
    assert reconcile(recovery, runtime=runtime, context=context).value.next_action == "reconcile"
    assert deliver(request, runtime=runtime, context=context).value.next_action == "reconcile"
    health = notification_health(key, reader=runtime, context=context)
    assert not health.due and health.oldest_pending_source_positions == (original.intent.event.cursor,)

    inbox.receipts[(request.dispatch_id, original.lookup.attempt_id)] = replace(
        inbox.lookup(original.lookup), state="accepted", retryable=False,
    )
    result = reconcile(recovery, runtime=runtime, context=context)
    assert result.value.state == "consumer_accepted"
    assert result.value.attempt_id == original.lookup.attempt_id
    assert len(inbox.calls) == 1


def test_retry_uses_original_bytes_and_current_route_revision(session):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)
    inbox.fail_mode = "refuse"
    inbox.retry_after = context.clock.now() + timedelta(seconds=900)
    first = deliver(request, runtime=runtime, context=context, jitter=lambda a, b: a)
    assert (first.outcome, first.value.state) == ("failed", "retry_due")
    assert first.value.next_due_at_utc == inbox.retry_after
    assert deliver(request, runtime=runtime, context=context).value.next_action == "wait"
    runtime.authority.route_revision = "r2"
    context.clock.advance(900)
    inbox.fail_mode = None
    inbox.retry_after = None
    second = deliver(request, runtime=runtime, context=context)
    assert second.value.state == "consumer_accepted"
    assert first.value.attempt_id != second.value.attempt_id
    assert inbox.calls[0].intent == inbox.calls[1].intent
    assert inbox.calls[1].lookup.route_revision == "r2"


def test_receipt_mismatch_cannot_promote_pending_or_accepted_state(session):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)
    deliver(request, runtime=runtime, context=context)
    call, = inbox.calls
    receipt = inbox.lookup(call.lookup)
    candidate = qualify(QualifyDeliveryRequest(call.lookup, replace(receipt, route_revision="foreign")),
                        context=context)
    assert candidate.value.state == "unknown"
    assert candidate.value.reason_code == "notification.receipt_mismatch"
    assert runtime.state.get_dispatch(request.scope_id, request.dispatch_id).state == "consumer_accepted"


def test_disable_or_revoke_cancels_an_unsent_obligation(session):
    runtime, _, context, _, inbox, spec = session
    request = _ready(session)
    configure_subscription(SubscriptionChange("disable", spec, 2), runtime=runtime, context=context)
    result = deliver(request, runtime=runtime, context=context)
    assert result.value.state == "cancelled"
    assert not inbox.calls


def test_reactivation_does_not_send_unsent_work_from_old_revision(session):
    runtime, _, context, _, inbox, spec = session
    request = _ready(session)
    configure_subscription(SubscriptionChange("disable", spec, 2), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", spec, 3), runtime=runtime, context=context)
    result = deliver(request, runtime=runtime, context=context)
    assert result.value.state == "cancelled"
    assert result.value.reason_code == "subscription.activation_changed"
    assert not inbox.calls


def test_revocation_after_prepare_uses_current_record_permission(session):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)
    runtime.authority.denied_actions.add("accept")
    result = deliver(request, runtime=runtime, context=context)
    assert result.value.state == "cancelled"
    assert not inbox.calls


def test_runtime_gate_rejects_wrong_bytes_even_with_a_good_per_call_gate(session, tmp_path):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)

    class WrongContentWriter:
        format = "jsonl"

        def write_batch(self, records, *, segment_id=None):
            record, = records
            return JournalWriteReceipt("confirmed", "barrier", ByteIdentity.of(b"different"),
                                       (record.record_id,), "immutable_read_back", "audit")

    good_writer = FileJournalWriter(LocalFileStore(tmp_path), "audit", writer_id="gate")
    good_gate = RequiredJournalGate(good_writer)
    strict = replace(runtime, audit_gate=RequiredJournalGate(WrongContentWriter()))
    result = deliver(request, runtime=strict, context=context, gate=good_gate, jitter=lambda a, b: a)
    assert (result.value.state, result.value.reason_code) == ("retry_due", "notification.audit_unconfirmed")
    assert not inbox.calls
    assert not list(tmp_path.rglob("*.jsonl"))

    context.clock.advance(30)
    strict = replace(runtime, audit_gate=good_gate)

    def check_audit_before_accept(handoff):
        during = runtime.state.get_dispatch(request.scope_id, request.dispatch_id)
        assert during.state == "in_flight"
        assert during.attempts[-1].lookup == handoff.lookup
        path, = tmp_path.rglob("*.jsonl")
        assert handoff.lookup.attempt_id in path.read_text(encoding="utf-8")

    inbox.on_accept = check_audit_before_accept
    confirmed = deliver(request, runtime=strict, context=context)
    assert confirmed.value.state == "consumer_accepted"
    assert len(inbox.calls) == 1


@pytest.mark.parametrize("loss,code", (("retention", "journal.cursor_expired"), ("epoch", "journal.epoch_mismatch")))
def test_source_evidence_loss_is_visible_and_recoverable(session, loss, code):
    runtime, key, context, source, inbox, _ = session
    request = _ready(session)
    original = runtime.state.get_dispatch(key.scope_id, request.dispatch_id)
    if loss == "retention":
        source.first_retained = 2
    else:
        source.epoch = "b"

    blocked = deliver(request, runtime=runtime, context=context)
    assert (blocked.outcome, blocked.value.state, blocked.value.next_action) == ("failed", "ready", "restore_evidence")
    assert blocked.diagnostics[0].code == code
    assert blocked.value.attempt_id is None
    assert not inbox.calls
    status = inspect_dispatch(key.scope_id, request.dispatch_id, reader=runtime, context=context)
    assert (status.reason_code, status.evidence_problem) == ("notification.evidence_unavailable", code)
    health = notification_health(key, reader=runtime, context=context)
    assert health.oldest_pending_source_positions == (original.intent.event.cursor,)
    assert health.due == (status,)
    assert deliver(request, runtime=runtime, context=context).value.next_action == "restore_evidence"
    stored = runtime.state.get_dispatch(key.scope_id, request.dispatch_id)
    assert stored.version == original.version + 1 and stored.attempts == ()
    audit = runtime.state.pending_audit(key.scope_id, limit=20)
    deferred, = (record for record in audit if record.kind == "notification.evidence_unavailable")
    assert deferred.payload["source_code"] == code

    source.first_retained, source.epoch = 1, "a"
    resumed = deliver(request, runtime=runtime, context=context)
    assert resumed.value.state == "consumer_accepted"
    assert len(inbox.calls) == 1 and inbox.calls[0].intent == original.intent
    assert notification_health(key, reader=runtime, context=context).oldest_pending_source_positions == ()


def test_retained_archive_supports_handoff_after_the_live_epoch_changes(session):
    runtime, key, context, archived, inbox, _ = session
    request = _ready(session)
    live = Source()
    live.epoch = "b"

    class ArchivalSource:
        def head(self, stream):
            return live.head(stream)

        def head_for_epoch(self, stream, epoch_id):
            return archived.head(stream) if epoch_id == archived.epoch else live.head(stream)

        def read_page(self, after, *, head, limits):
            source = archived if head.epoch_id == archived.epoch else live
            return source.read_page(after, head=head, limits=limits)

    runtime = replace(runtime, sources=(replace(runtime.source_for(key.stream), source=ArchivalSource()),))
    assert notification_health(key, reader=runtime, context=context).head.epoch_id == "b"
    assert deliver(request, runtime=runtime, context=context).value.state == "consumer_accepted"
    assert inbox.calls[0].intent.event.cursor.epoch_id == "a"


def test_changed_source_bytes_are_quarantined(session):
    runtime, key, context, source, inbox, _ = session
    request = _ready(session)
    source.records[0] = replace(source.records[0], payload={**source.records[0].payload, "size_bytes": 221})
    result = deliver(request, runtime=runtime, context=context)
    assert (result.value.state, result.value.reason_code) == ("quarantined", "journal.record_identity_mismatch")
    assert not inbox.calls
    assert notification_health(key, reader=runtime, context=context).oldest_pending_source_positions == ()


def test_new_projection_requires_a_new_dispatch_identity_for_historical_delivery(session):
    runtime, key, context, _, inbox, spec = session
    old = _ready(session)
    topic, projection = runtime.catalog.resolve(spec)
    v2 = replace(topic, version=2, projections=(replace(projection, version=2),))
    runtime = replace(runtime, catalog=build_catalog(topics=(v2,)))
    updated = replace(spec, topic_version=2, projection_version=2)
    configure_subscription(SubscriptionChange("update", updated, 2), runtime=runtime, context=context)
    stopped = deliver(old, runtime=runtime, context=context)
    assert (stopped.value.state, stopped.value.reason_code) == ("cancelled", "notification.subscription_changed")
    assert not inbox.calls

    current = replace(key, replay_id="same-subscription")
    until = context.clock.now() + timedelta(days=1)
    register_replay(current, 1, 1, until, runtime=runtime, context=context)
    replay = prepare(PrepareRequest(current, mode="replay"), runtime=runtime, context=context)
    assert (replay.value.prepared, replay.value.duplicate) == (0, 1)

    replacement = replace(updated, subscription_id="new-subscription")
    configure_subscription(SubscriptionChange("create", replacement), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", replacement, 1), runtime=runtime, context=context)
    fresh = replace(current, subscription_id=replacement.subscription_id, replay_id="new-projection")
    register_replay(fresh, 1, 1, until, runtime=runtime, context=context)
    assert prepare(PrepareRequest(fresh, mode="replay"), runtime=runtime, context=context).value.prepared == 1
    row, = runtime.state.scan_dispatches(fresh.scope_id, fresh.subscription_id, limit=2)
    assert row.intent.dispatch_id != old.dispatch_id
    assert deliver(DeliverRequest(fresh.scope_id, row.intent.dispatch_id), runtime=runtime, context=context).value.state == "consumer_accepted"


def test_claim_excludes_competing_workers(session):
    runtime, _, context, _, inbox, _ = session
    request = _ready(session)
    entered, release = Event(), Event()

    def hold(_):
        entered.set()
        assert release.wait(timeout=5)

    inbox.on_accept = hold
    with ThreadPoolExecutor(2) as executor:
        first = executor.submit(deliver, request, runtime=runtime, context=context)
        assert entered.wait(timeout=5)
        try:
            contender = deliver(request, runtime=runtime, context=context)
            assert contender.value.state == "in_flight"
        finally:
            release.set()
        assert first.result(timeout=5).value.state == "consumer_accepted"
    assert len(inbox.calls) == 1


def test_managed_execution_requires_scoped_real_bindings(session):
    runtime, key, _, _, inbox, _ = session
    request = _ready(session)
    result = deliver(request, runtime=runtime, context=ExecutionContext(profile="managed"))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "provider.capability_missing"
    assert runtime.state.get_dispatch(key.scope_id, request.dispatch_id).state == "ready"
    assert not inbox.calls
