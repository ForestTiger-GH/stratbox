"""Offline Rosstat original -> owner-confirmed revision -> notification.

Only a synthetic HTML and fake PDF are used. No official network, Git or
Telegram calls. The test deliberately starts with a synthetic confirmed
old version to demonstrate a byte revision without a claimed publisher issue.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from stratbox.core.network import HttpResponse
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.operations.source.originals import OriginalDestination
from stratbox.core.operations.source.version_comparison import (
    CompareOriginalVersionsRequest, OriginalVersion, compare_original_versions,
)
from stratbox.domains.rosstat.publications.contracts import (
    DiscoverRosstatRequest, AcquireRosstatToStoreRequest,
)
from stratbox.domains.rosstat.operations.publications import discover, acquire_to_store
from stratbox.shared.evidence import PublicationReceipt, SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import (
    ConfirmedOriginalPublication, PublishedArtifactRef,
)
from stratbox.core.observability import (
    RecordMemorySink, SnapshotJournalSource, StreamKey,
    fact_from_original_version_commit, record_from_fact,
)
from stratbox.core.notifications import (
    AccessDecision, CheckpointKey, ConsumerBinding, DeliverRequest, HandoffReceipt,
    MemoryNotificationState, NotificationRoute, NotificationRuntime, PrepareRequest,
    SourceBinding, SubscriptionChange, SubscriptionSpec, build_catalog,
    configure_subscription, deliver, prepare, register_replay,
)


class OfflineTransport:
    def __init__(self, body):
        self.body = body

    def exchange_into(self, request, sink, *, cancelled=None):
        from stratbox.core.network import HttpStreamResponse
        sink.write(self.body)
        meta = HttpResponse(
            200, b"", {"content-type": "application/pdf"},
            datetime.now(timezone.utc), "https://rosstat.gov.ru",
        )
        return HttpStreamResponse(meta, ByteIdentity.of(self.body))


class Authority:
    def authorize(self, request):
        if request.actor_id != "demo":
            return AccessDecision("denied")
        allowed = frozenset({
            "source_id", "series_id", "issue_id", "asset_id", "transition_id",
            "change", "previous_sha256", "previous_transition_id",
            "current_sha256", "size_bytes", "mode", "owner_id", "destination_id",
            "artifact_ref", "publication_proof_ref",
        })
        return AccessDecision(
            "allow", allowed,
            frozenset({"event_ref", "occurred_at_utc", "subject"}),
            "demo-grant", "demo-route",
        )


class Inbox:
    def __init__(self):
        self.delivered = {}

    def accept(self, handoff):
        key = handoff.lookup
        if key not in self.delivered:
            self.delivered[key] = HandoffReceipt(
                key.dispatch_id, key.attempt_id, key.route, key.route_revision,
                key.payload_identity, "accepted",
                datetime.now(timezone.utc), "in-memory",
            )
        return self.delivered[key]

    def lookup(self, query):
        return self.delivered.get(query)


def value(result):
    if result.outcome != "succeeded":
        raise RuntimeError(str(result.diagnostics))
    return result.value


def main():
    series = "rosstat.socioeconomic_russia"
    html = b'<a href="/storage/mediabank/osn-08-2026.pdf">2026-08</a>'
    page = SourcePayload(html, "text/html", series + ".index", charset="utf-8")
    index = value(discover(DiscoverRosstatRequest(series, page)))
    asset, = index.qualified_assets
    original = b"%PDF-1.4\n% offline sample\n%%EOF\n"

    with TemporaryDirectory() as location:
        saved = value(acquire_to_store(
            AcquireRosstatToStoreRequest(asset, OriginalDestination("2026-08.pdf")),
            transport=OfflineTransport(original),
            store=LocalFileStore(location),
        ))
        assert Path(location, "2026-08.pdf").read_bytes() == original
        candidate = OriginalVersion(asset.key.source_id, saved.source.storage.identity)
        # Synthetic pre-existing accepted baseline, with a parent transition.
        prior = OriginalVersion(asset.key.source_id, ByteIdentity.of(b"old"), "f"*64)
        comparison = value(compare_original_versions(
            CompareOriginalVersionsRequest(candidate, "available", prior)
        ))
        verified = PublishedArtifactRef(
            "demo", asset.key.source_id,
            candidate.identity.sha256, candidate.identity, "verified-readback",
        )
        publication = ConfirmedOriginalPublication(
            PublicationReceipt(
                "demo", "demo", candidate.source_id,
                comparison.transition_id, candidate.identity, "confirmed",
            ),
            verified,
        )
        fact = fact_from_original_version_commit(
            comparison, publication, asset=asset.key.identity,
            mode="live", occurred_at_utc=datetime.now(timezone.utc),
        )
        sink = RecordMemorySink()
        sink.capture(record_from_fact(fact))
        stream = StreamKey("demo", "source-events", "local")
        source = SnapshotJournalSource(
            sink.finalize_generation(), stream,
            source_authority_id="demo", epoch_id="offline",
        )
        route = NotificationRoute("offline_inbox", "originals", "demo")
        state = MemoryNotificationState()
        inbox = Inbox()
        runtime = NotificationRuntime(
            "demo", build_catalog(), Authority(), state,
            (SourceBinding(stream, "demo", "local_snapshot", source),),
            (ConsumerBinding("demo", route, "in_process", inbox),),
        )
        spec = SubscriptionSpec(
            "demo", "source_updates", "demo", (stream,), route,
            "source.original_version_committed", 1, "original_version_public", 1,
        )
        configure_subscription(SubscriptionChange("create", spec), runtime=runtime)
        configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime)
        checkpoint = CheckpointKey("demo", "source_updates", stream, replay_id="offline-demo")
        register_replay(
            checkpoint, 1, source.head(stream).tail_offset,
            datetime.now(timezone.utc) + timedelta(minutes=15), runtime=runtime,
        )
        report = value(prepare(PrepareRequest(checkpoint, mode="replay"), runtime=runtime))
        assert report.prepared == 1
        dispatch, = state.scan_dispatches("demo", "source_updates", limit=2)
        outcome = value(deliver(
            DeliverRequest("demo", dispatch.intent.dispatch_id), runtime=runtime,
        ))
        assert outcome.state == "consumer_accepted"
        print(series, candidate.identity.sha256, outcome.state)


if __name__ == "__main__":
    main()
