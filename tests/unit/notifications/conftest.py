from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from stratbox.core.execution import ExecutionContext
from stratbox.core.notifications import (
    AccessDecision, CheckpointKey, ConsumerBinding, HandoffReceipt, MemoryNotificationState,
    NotificationRoute, NotificationRuntime, SourceBinding, SubscriptionChange, SubscriptionSpec,
    build_catalog, configure_subscription,
)
from stratbox.core.observability import (
    DomainFact, JournalEntry, JournalHead, JournalPage, ObjectRef, StreamKey, record_from_fact,
)

TIME = datetime(2026, 11, 17, 9, tzinfo=timezone.utc)
STREAM = StreamKey("public", "updates", "main")
ROUTE = NotificationRoute("inbox", "updates", "team")


class Clock:
    def __init__(self):
        self.at = TIME

    def now(self):
        return self.at

    def monotonic(self):
        return 12.0

    def advance(self, seconds):
        self.at += timedelta(seconds=seconds)


class Source:
    def __init__(self):
        self.records = []
        self.epoch = "a"
        self.first_retained = 1

    def head(self, stream):
        assert stream == STREAM
        n = len(self.records)
        return JournalHead(STREAM, self.epoch, f"head-{n}", "publisher", "local_snapshot", self.first_retained, n)

    def read_page(self, after, *, head, limits):
        head.check(after)
        first = after.last_offset
        end = min(head.tail_offset, first + limits.max_positions)
        return JournalPage(head, after, tuple(
            JournalEntry.from_record(i + 1, self.records[i], head.head_ref)
            for i in range(first, end)
        ), capture_coverage="complete", domain_coverage="complete")


def byte_event(event="transition-1", observation="obs-1", *, old="a", new="b", version=1):
    fact = DomainFact("source.bytes_changed", ObjectRef("source", "official"), event, TIME, {
        "data_version": version, "source_id": "official", "transition_id": event,
        "old_sha256": old * 64, "new_sha256": new * 64, "size_bytes": 220,
        "time_basis": "observed_change",
    }, observation_id=observation)
    if version != 1:
        # A raw historical record may carry a future data version.
        record = record_from_fact(replace(fact, payload=fact.payload | {"data_version": 1}))
        return replace(record, payload=fact.payload)
    return record_from_fact(fact)


class Authority:
    def __init__(self):
        self.denied_actions = set()
        self.unavailable_actions = set()
        self.route_revision = "r1"
        self.fields = frozenset({
            "source_id", "transition_id", "old_sha256", "new_sha256", "size_bytes", "time_basis",
            "mode", "change", "reference_date", "series_id", "artifact_ref", "regions",
        })

    def authorize(self, request):
        if request.actor_id != request.spec.owner_id or request.spec.scope_id != "public":
            return AccessDecision("denied")
        if request.action in self.unavailable_actions:
            raise OSError("private endpoint")
        if request.action in self.denied_actions:
            return AccessDecision("denied")
        return AccessDecision("allow", self.fields, frozenset({"event_ref", "occurred_at_utc"}),
                              "public_grant", self.route_revision)


class Inbox:
    def __init__(self, clock):
        self.clock = clock
        self.calls = []
        self.receipts = {}
        self.fail_mode = None
        self.retry_after = None
        self.on_accept = None

    def accept(self, handoff):
        request = handoff.lookup
        self.calls.append(handoff)
        if self.on_accept:
            self.on_accept(handoff)
        if self.fail_mode == "unavailable":
            raise OSError("lost")
        refused = self.fail_mode in {"refuse", "pending_refusal"}
        receipt = HandoffReceipt(
            request.dispatch_id, request.attempt_id, request.route, request.route_revision,
            request.payload_identity, "not_accepted" if refused else "accepted", self.clock.now(),
            evidence_ref="proof-" + request.attempt_id, retryable=refused, retry_after_utc=self.retry_after,
            final_rejection=self.fail_mode == "refuse",
        )
        self.receipts[(request.dispatch_id, request.attempt_id)] = receipt
        if self.fail_mode == "lost_response":
            raise TimeoutError
        return receipt

    def lookup(self, request):
        return self.receipts.get((request.dispatch_id, request.attempt_id))


@pytest.fixture
def session():
    clock = Clock()
    context = ExecutionContext(clock=clock)
    source = Source()
    authority = Authority()
    inbox = Inbox(clock)
    state = MemoryNotificationState()
    runtime = NotificationRuntime("owner", build_catalog(), authority, state,
                                  (SourceBinding(STREAM, "publisher", "local_snapshot", source),),
                                  (ConsumerBinding("public", ROUTE, "in_process", inbox),))
    spec = SubscriptionSpec("public", "bytes_alerts", "owner", (STREAM,), ROUTE, "source.bytes_changed", 1,
                            "bytes_change_public", 1)
    key = CheckpointKey("public", "bytes_alerts", STREAM)
    configure_subscription(SubscriptionChange("create", spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime, context=context)
    return runtime, key, context, source, inbox, spec
