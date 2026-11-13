from dataclasses import replace
from threading import Event

from stratbox.data import ByteIdentity, PublicationReceipt
from stratbox.execution import ExecutionContext
from stratbox.notifications import (
    DeliverRequest,
    NotificationPolicy,
    NotificationRoute,
    PrepareRequest,
    QualifyDeliveryRequest,
    PublicationConfirmed,
    SendReceipt,
    deliver,
    prepare,
    qualify,
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
    reconciled = qualify(
        QualifyDeliveryRequest(intent, SendReceipt(intent.effect_key, "not_accepted"))
    )
    accepted = deliver(DeliverRequest(intent, ROUTE, reconciled.value), transport=fresh)
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


def test_managed_acceptance_checks_publication_recipient_and_reconciles_restart(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import sqlite3

    from stratbox.base.capabilities import ProviderBinding
    from stratbox.notifications import ReconcileDeliveryRequest, reconcile
    from stratbox.notifications.operations import DELIVER

    ledger = tmp_path / "receipts.sqlite3"
    with sqlite3.connect(ledger) as db:
        db.execute("create table sent (key text primary key, digest text, recipient text)")
    request = replace(prepare_request("first"), route_revision="v1")
    intent = prepare(request).value.intent
    authentic_event = intent.event_identity
    authentic_payload = intent.payload_identity
    old_route = intent.route

    class Channel:
        route = old_route
        revision = "v1"
        generation = 1
        active_generation = 1
        audit = True
        lost_ack = False

        def acknowledgement(self, item, state):
            return SendReceipt(
                item.effect_key, state, "sink-ack" if state == "accepted" else None,
                item.route, item.payload_identity, item.route_revision,
            )

        def lookup(self, item):
            with sqlite3.connect(ledger) as db:
                row = db.execute("select digest, recipient from sent where key = ?", (item.effect_key,)).fetchone()
            if row == (item.payload_identity.sha256, item.route.destination_id):
                return self.acknowledgement(item, "accepted")
            return self.acknowledgement(item, "unknown")

        def send_admitted(self, item):
            if (not self.audit or self.generation != self.active_generation
                    or item.event_identity != authentic_event or item.payload_identity != authentic_payload
                    or item.route != self.route or item.route_revision != self.revision):
                return self.acknowledgement(item, "not_accepted")
            with sqlite3.connect(ledger) as db:
                db.execute("insert or ignore into sent values (?,?,?)",
                           (item.effect_key, item.payload_identity.sha256, item.route.destination_id))
            if self.lost_ack:
                raise TimeoutError("ack lost after channel committed")
            return self.lookup(item)

    def context(channel):
        capability = DELIVER.capability("notification", managed=True)
        return ExecutionContext(profile="managed", bindings=(
            ProviderBinding("receiving-channel", capability, "ready", channel, "recipient-scope"),
        ))

    def send(channel, item=intent, previous=None):
        return deliver(DeliverRequest(item, item.route, previous), transport=channel, context=context(channel))

    channel = Channel()
    forged = prepare(replace(prepare_request("fake"), route_revision="v1")).value.intent
    assert send(channel, forged).value.state == "not_accepted"
    other_payload = prepare(replace(prepare_request("first", digest=b"fake"), route_revision="v1")).value.intent
    assert other_payload.effect_key == intent.effect_key
    assert send(channel, other_payload).value.state == "not_accepted"
    channel.route = NotificationRoute("updates", "moved")
    assert send(channel).value.state == "not_accepted"
    channel.route = old_route
    channel.audit = False
    assert send(channel).value.state == "not_accepted"
    channel.audit = True
    channel.active_generation = 2
    assert send(channel).value.state == "not_accepted"
    channel.generation = 2
    with sqlite3.connect(ledger) as db:
        assert db.execute("select count(*) from sent").fetchone() == (0,)

    channel.lost_ack = True
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = list(pool.map(lambda _: send(channel), range(2)))
    assert {result.outcome for result in attempts} == {"unknown"}
    assert attempts[0].diagnostics[0].retry_disposition == "reconcile"
    with sqlite3.connect(ledger) as db:
        assert db.execute("select count(*) from sent").fetchone() == (1,)
    channel = Channel()
    proof = reconcile(ReconcileDeliveryRequest(intent), transport=channel, context=context(channel))
    assert proof.outcome == "succeeded" and proof.value.state == "accepted"
    assert send(channel, previous=attempts[0].value).value == proof.value
    assert not send(channel, previous=attempts[0].value).effects
    unverified = qualify(QualifyDeliveryRequest(intent, channel.acknowledgement(intent, "accepted")),
                         context=context(channel))
    assert unverified.diagnostics[0].code == "notification.owner_lookup_required"
