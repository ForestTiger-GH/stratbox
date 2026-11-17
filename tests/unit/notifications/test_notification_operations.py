from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
import json
from threading import Event

from stratbox.execution import ExecutionContext
from stratbox.notifications import (
    DeliverRequest, PrepareRequest, QualifyDeliveryRequest, ReconcileDeliveryRequest, SubscriptionChange,
    configure_subscription, deliver, inspect_dispatch, notification_health, prepare, qualify, reconcile,
)

from conftest import byte_event


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
