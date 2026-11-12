from dataclasses import replace
from threading import Event

from stratbox.data import ByteIdentity, PublicationReceipt
from stratbox.execution import ExecutionContext
from stratbox.notifications import (
    DeliverRequest,
    NotificationPolicy,
    NotificationRoute,
    PrepareRequest,
    PublicationConfirmed,
    SendReceipt,
    deliver,
    prepare,
)


ROUTE = NotificationRoute("updates", "subscriber")


class Transport:
    def __init__(self, state="accepted", acknowledgement="ack"):
        self.attempts = 0
        self.state = state
        self.acknowledgement = acknowledgement

    def send(self, intent):
        self.attempts += 1
        if self.state == "lost":
            raise TimeoutError("request reached channel")
        return SendReceipt(intent.effect_key, self.state, self.acknowledgement)


def prepare_request(transition, *, confirmation="confirmed", digest=b"release"):
    receipt = PublicationReceipt(
        "publisher",
        "destination",
        "2026-11-10",
        transition,
        ByteIdentity.of(digest),
        confirmation,
    )
    return PrepareRequest(
        PublicationConfirmed(receipt, "revised"), NotificationPolicy(), ROUTE
    )


def test_confirmed_transitions_and_dry_run():
    one = prepare(prepare_request("first")).value.intent
    same_data = prepare(prepare_request("second")).value.intent
    assert one.effect_key != same_data.effect_key
    assert (
        prepare(prepare_request("first", confirmation="unknown")).value.intent is None
    )
    assert (
        prepare(replace(prepare_request("first"), dry_run=True)).value.reason
        == "policy.dry_run"
    )
    assert prepare(prepare_request("first")).value.intent == one


def test_lost_ack_is_reconciled_and_never_silently_retried():
    intent = prepare(prepare_request("first")).value.intent
    lost = Transport(state="lost")
    unknown = deliver(DeliverRequest(intent, ROUTE), transport=lost)
    assert unknown.outcome == "unknown"
    assert unknown.effects[0].state == "unknown"
    fresh = Transport()
    blocked = deliver(DeliverRequest(intent, ROUTE, unknown.value), transport=fresh)
    assert blocked.outcome == "unknown" and fresh.attempts == 0
    conflict = prepare(prepare_request("first", digest=b"other")).value.intent
    assert (
        deliver(DeliverRequest(conflict, ROUTE, unknown.value), transport=fresh)
        .diagnostics[0]
        .code
        == "notification.payload_conflict"
    )
    assert fresh.attempts == 0
    accepted = deliver(
        DeliverRequest(intent, ROUTE, unknown.value, idempotent_channel_verified=True),
        transport=fresh,
    )
    assert accepted.outcome == "succeeded"
    assert fresh.attempts == 1
    assert (
        deliver(DeliverRequest(intent, ROUTE, accepted.value), transport=fresh).outcome
        == "succeeded"
    )
    assert fresh.attempts == 1


def test_refused_and_cancelled_delivery():
    intent = prepare(prepare_request("first")).value.intent
    transport = Transport(state="not_accepted")
    refusal = deliver(DeliverRequest(intent, ROUTE), transport=transport)
    assert refusal.outcome == "failed"
    assert refusal.value.next_action == "retry"
    cancel = Event()
    cancel.set()
    result = deliver(
        DeliverRequest(intent, ROUTE),
        transport=transport,
        context=ExecutionContext(cancellation=cancel),
    )
    assert result.outcome == "cancelled"
    assert transport.attempts == 1


def test_separate_receipt_qualification_can_unlock_a_retry():
    from stratbox.notifications import QualifyDeliveryRequest, qualify

    intent = prepare(prepare_request("first")).value.intent
    stale = qualify(
        QualifyDeliveryRequest(intent, SendReceipt("different", "accepted", "ack"))
    )
    assert stale.outcome == "unknown" and not stale.effects
    resolved = qualify(
        QualifyDeliveryRequest(intent, SendReceipt(intent.effect_key, "not_accepted"))
    )
    assert resolved.outcome == "succeeded" and resolved.value.next_action == "retry"
    transport = Transport()
    assert (
        deliver(
            DeliverRequest(intent, ROUTE, resolved.value), transport=transport
        ).outcome
        == "succeeded"
    )
    assert transport.attempts == 1
