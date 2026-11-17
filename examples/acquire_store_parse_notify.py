"""Run the notification path with recorded source bytes and an in-process inbox."""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from stratbox.system.base.filestore import LocalFileStore
from stratbox.system.base.net import HttpResponse
from stratbox.system.execution import ExecutionContext
from stratbox.system.execution.originals import OriginalDestination, SaveOriginalRequest, save_original
from stratbox.domains import cbr_offices
from stratbox.system.notifications import (
    AccessDecision, CheckpointKey, ConsumerBinding, DeliverRequest, HandoffReceipt,
    MemoryNotificationState, NotificationRoute, NotificationRuntime, PrepareRequest, SourceBinding,
    SubscriptionChange, SubscriptionSpec, build_catalog, configure_subscription, deliver, prepare,
    register_replay,
)
from stratbox.system.observability import RecordMemorySink, SnapshotJournalSource, StreamKey, capture_operation_result


class RecordedSource:
    def __init__(self, original):
        self.original = original

    def exchange(self, request, *, cancelled=None):
        return HttpResponse(
            200, self.original, {"content-type": "text/html"},
            datetime(2026, 11, 11, tzinfo=timezone.utc), "https://www.cbr.ru",
        )


class DemoAuthority:
    def authorize(self, request):
        if request.actor_id == request.spec.owner_id and request.spec.scope_id == "demo":
            return AccessDecision("allow", frozenset({"identity", "status"}),
                                  frozenset({"event_ref", "occurred_at_utc", "subject"}),
                                  "demo-grant", "demo-route-1")
        return AccessDecision("denied")


class InProcessInbox:
    def __init__(self, clock):
        self.clock = clock
        self.receipts = {}

    def accept(self, handoff):
        key = handoff.lookup
        existing = self.lookup(key)
        if existing is not None:
            return existing
        self.receipts[key] = HandoffReceipt(
            key.dispatch_id, key.attempt_id, key.route, key.route_revision,
            key.payload_identity, "accepted", self.clock.now(), "offline-inbox",
        )
        return self.receipts[key]

    def lookup(self, query):
        return self.receipts.get(query)


def require_value(result):
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    transport = RecordedSource(args.html.read_bytes())
    sink = RecordMemorySink()
    context = ExecutionContext(sink=sink)
    acquired = require_value(cbr_offices.acquire(
        cbr_offices.AcquireOfficesRequest(timezone.utc), transport=transport, context=context,
    ))
    stored_result = save_original(
        SaveOriginalRequest(acquired.payload, OriginalDestination(args.archive.name)),
        store=LocalFileStore(args.archive.parent), context=context,
    )
    stored = require_value(stored_result)
    capture_operation_result(stored_result, sink)
    parsed = require_value(cbr_offices.parse(
        cbr_offices.ParseOfficesRequest(acquired.payload, acquired.capture_date), context=context,
    ))

    stream = StreamKey("demo", "journal", "local")
    source = SnapshotJournalSource(sink.finalize_generation(), stream, source_authority_id="demo", epoch_id="run")
    route = NotificationRoute("local_inbox", "archive-update", "demo")
    state = MemoryNotificationState()
    runtime = NotificationRuntime(
        "demo", build_catalog(), DemoAuthority(), state,
        (SourceBinding(stream, "demo", "local_snapshot", source),),
        (ConsumerBinding("demo", route, "in_process", InProcessInbox(context.clock)),),
    )
    spec = SubscriptionSpec("demo", "archive_update", "demo", (stream,), route,
                            "material.stored", 1, "stored_material", 1)
    configure_subscription(SubscriptionChange("create", spec), runtime=runtime)
    configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime)
    replay = CheckpointKey("demo", "archive_update", stream, replay_id="review-snapshot")
    register_replay(replay, 1, source.head(stream).tail_offset,
                    context.clock.now() + timedelta(minutes=15), runtime=runtime)
    processed = require_value(prepare(PrepareRequest(replay, mode="replay"), runtime=runtime))
    if processed.prepared:
        row, = state.scan_dispatches("demo", "archive_update", limit=2)
        result = require_value(deliver(DeliverRequest("demo", row.intent.dispatch_id), runtime=runtime))
        print(parsed.dataset_version.identity.sha256, result.state, row.intent.dispatch_id)
    else:
        print(parsed.dataset_version.identity.sha256, stored.storage.status, "no_matching_effect")


if __name__ == "__main__":
    main()
