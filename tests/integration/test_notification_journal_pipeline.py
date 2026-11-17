"""Provider conformance against real file reads and an isolated durable transaction log."""
from contextlib import closing
from datetime import datetime, timezone
import sqlite3

from stratbox.system.base.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.system.base.filestore import LocalFileStore
from stratbox.system.execution import ExecutionContext
from stratbox.system.notifications import (
    AccessDecision, CheckpointKey, ConsumerBinding, DeliverRequest, ExternalDeliveryReceipt,
    HandoffReceipt, MemoryNotificationState, NotificationRoute, NotificationRuntime,
    NotificationTopic, PrepareRequest, Projection, ReconcileDeliveryRequest, SourceBinding,
    SubscriptionChange, SubscriptionSpec, build_catalog, configure_subscription, decode_state_mutation,
    deliver, encode_state_mutation, prepare, project_downstream, reconcile, record_external_delivery,
)
from stratbox.system.observability import (
    DomainFact, FieldRule, FieldSchemaRegistry, FileJournalReader, FileJournalSource,
    FileJournalWriter, IndexedSegment, JournalHead, ObjectRef, RecordDataSchema, SegmentDescriptor,
    StreamKey, ValueRule, record_from_fact,
)

TIME = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
STREAM = StreamKey("public", "publication", "default")
ROUTE = NotificationRoute("inbox", "update", "group")


class Clock:
    def now(self):
        return TIME

    def monotonic(self):
        return 1.0


class TransactionFixture:
    """Small append-only host for testing fresh processes and real atomic writes."""

    durable = True

    def __init__(self, path):
        self.path = path
        self.lose_reply = False
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS commits (seq INTEGER PRIMARY KEY, command TEXT UNIQUE, body BLOB)")

    def _load(self, db):
        model = MemoryNotificationState()
        for (body,) in db.execute("SELECT body FROM commits ORDER BY seq"):
            assert model.commit(decode_state_mutation(body)).state == "confirmed"
        return model

    def commit(self, command):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            model = self._load(db)
            receipt = model.commit(command)
            if receipt.state == "confirmed":
                db.execute("INSERT OR IGNORE INTO commits(command, body) VALUES (?, ?)",
                           (command.command_id, encode_state_mutation(command)))
        if self.lose_reply:
            self.lose_reply = False
            raise OSError("response lost after commit")
        return receipt

    def __getattr__(self, name):
        with closing(sqlite3.connect(self.path)) as db:
            return getattr(self._load(db), name)


class InboxFixture:
    def __init__(self, path, state, *, lose_reply=False):
        self.path, self.state, self.lose_reply = path, state, lose_reply
        self.calls = 0
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS inbox (id TEXT PRIMARY KEY, attempt TEXT, hash TEXT, fence INTEGER)")

    def accept(self, handoff):
        self.calls += 1
        key, intent = handoff.lookup, handoff.intent
        current = self.state.get_subscription(intent.scope_id, intent.subscription_id)
        claim = self.state.get_dispatch(key.scope_id, key.dispatch_id)
        assert current.status == "active" and current.revision == handoff.subscription_revision
        assert claim.state == "in_flight" and claim.attempts[-1].lookup == key
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR IGNORE INTO inbox VALUES (?, ?, ?, ?)",
                       (key.dispatch_id, key.attempt_id, key.payload_identity.sha256, key.fence))
        if self.lose_reply:
            raise TimeoutError("acceptance reply lost")
        return self.lookup(key)

    def lookup(self, key):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT attempt, hash, fence FROM inbox WHERE id = ?", (key.dispatch_id,)).fetchone()
        if row != (key.attempt_id, key.payload_identity.sha256, key.fence):
            return None
        return HandoffReceipt(key.dispatch_id, key.attempt_id, key.route, key.route_revision,
                              key.payload_identity, "accepted", TIME, "inbox-confirmed")


class Authority:
    def __init__(self, fields):
        self.fields = frozenset(fields)

    def authorize(self, request):
        if request.actor_id != request.spec.owner_id or request.spec.scope_id != STREAM.scope_id:
            return AccessDecision("denied")
        return AccessDecision("allow", self.fields, frozenset({"event_ref", "occurred_at_utc"}),
                              "local-grant", "route-1")


def _context(runtime, source, consumer):
    pairs = [
        ("notification_authority", runtime.authority, {"scope_bound"}),
        ("notification_state", runtime.state, {"atomic_commit"}),
        ("journal_source", source, {"scope_bound", "position_bound"}),
        ("notification", consumer, {"recipient_bound", "durable_acceptance", "idempotent_acceptance"}),
    ]
    bindings = tuple(ProviderBinding(role, CapabilityRequirement(role, guarantees=frozenset(guarantees)),
                                     "ready", provider, STREAM.scope_id)
                     for role, provider, guarantees in pairs)
    return ExecutionContext(clock=Clock(), profile="managed", bindings=bindings)


def _source(tmp_path, records):
    store = LocalFileStore(tmp_path)
    writer = FileJournalWriter(store, "journal", writer_id="owner")
    index = ()
    if records:
        receipt = writer.write_batch(records)
        assert receipt.state == "confirmed"
        index = (IndexedSegment(1, SegmentDescriptor.from_receipt(receipt)),)
    head = JournalHead(STREAM, "epoch", f"head-{len(records)}", "publisher", "resumable", 1, len(records))
    return FileJournalSource(FileJournalReader(store, namespace=writer.namespace), head, index)


def _runtime(store, source, inbox, catalog, fields):
    return NotificationRuntime("owner", catalog, Authority(fields), store,
                               (SourceBinding(STREAM, "publisher", "resumable", source),),
                               (ConsumerBinding(STREAM.scope_id, ROUTE, "durable_inbox", inbox),))


def _publication(transition, mode="live"):
    payload = {
        "data_version": 1, "series_id": "official", "reference_date": "2026-11-01",
        "transition_id": transition, "change": "updated", "mode": mode,
        "artifact_ref": {"scope_id": "public", "artifact_id": "reference", "version_id": transition,
                         "sha256": "c" * 64, "size_bytes": 400},
    }
    return record_from_fact(DomainFact("publication.committed", ObjectRef("series", "official"),
                                      transition, TIME, payload, observation_id=transition))


def test_publication_and_receipt_survive_state_and_inbox_restart(tmp_path):
    catalog = build_catalog()
    state = TransactionFixture(tmp_path / "state.db")
    inbox = InboxFixture(tmp_path / "inbox.db", state, lose_reply=True)
    fields = {"series_id", "reference_date", "transition_id", "change", "mode", "artifact_ref"}
    empty = _source(tmp_path, ())
    runtime = _runtime(state, empty, inbox, catalog, fields)
    context = _context(runtime, empty, inbox)
    spec = SubscriptionSpec("public", "publication", "owner", (STREAM,), ROUTE,
                            "publication.committed", 1, "publication_summary", 1)
    key = CheckpointKey("public", "publication", STREAM)
    configure_subscription(SubscriptionChange("create", spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime, context=context)
    live = _source(tmp_path, (_publication("backfill", "backfill"), _publication("live")))
    runtime = _runtime(state, live, inbox, catalog, fields)
    context = _context(runtime, live, inbox)
    state.lose_reply = True
    selected = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert selected.outcome == "succeeded", selected.diagnostics
    assert (selected.value.prepared, selected.value.skipped, selected.value.checkpoint.last_offset) == (1, 1, 2)
    row, = state.scan_dispatches("public", "publication", limit=2)
    attempt = deliver(DeliverRequest("public", row.intent.dispatch_id), runtime=runtime, context=context)
    assert (attempt.outcome, attempt.value.state) == ("unknown", "unknown")
    recovered_state = TransactionFixture(tmp_path / "state.db")
    recovered_inbox = InboxFixture(tmp_path / "inbox.db", recovered_state)
    recovered_source = _source(tmp_path, (_publication("backfill", "backfill"), _publication("live")))
    recovered_runtime = _runtime(recovered_state, recovered_source, recovered_inbox, catalog, fields)
    recovered_context = _context(recovered_runtime, recovered_source, recovered_inbox)
    outcome = reconcile(ReconcileDeliveryRequest("public", row.intent.dispatch_id, attempt.value.attempt_id),
                        runtime=recovered_runtime, context=recovered_context)
    assert (outcome.outcome, outcome.value.state) == ("succeeded", "consumer_accepted")
    assert recovered_state.get_checkpoint(key).last_offset == 2
    assert (inbox.calls, recovered_inbox.calls) == (1, 0)
    stage = record_external_delivery(ExternalDeliveryReceipt(
        "public", row.intent.dispatch_id, "transport-attempt", "inbox", "transport_accepted",
        "unknown", TIME,
    ))
    assert stage.kind == "notification.transport_accepted" and stage.payload["state"] == "unknown"
    observed = project_downstream((stage,), scope_id="public", dispatch_id=row.intent.dispatch_id,
                                  consumer_id="inbox")
    assert [(item.stage, item.state) for item in observed] == [("transport_accepted", "unknown")]
    assert recovered_state.get_dispatch("public", row.intent.dispatch_id).state == "consumer_accepted"


def test_forecast_extension_with_owner_commit_and_closed_projection(tmp_path):
    names = ("forecast_id", "revision_id", "decision_id", "decision_code")
    token = ValueRule("token")
    fields = tuple(FieldRule(name, token, classification="public") for name in names)
    extension = RecordDataSchema("domain_fact", "forecast.review_decided", 1, fields)
    topic = NotificationTopic("forecast.review_decided", 1, (extension.key,),
                              (Projection("review_result", 1, fields),), "fact", names)
    catalog = build_catalog(FieldSchemaRegistry((extension,)), (topic,))
    state = TransactionFixture(tmp_path / "notifications.db")
    inbox = InboxFixture(tmp_path / "inbox.db", state)
    source = _source(tmp_path, ())
    runtime = _runtime(state, source, inbox, catalog, names)
    context = _context(runtime, source, inbox)
    spec = SubscriptionSpec("public", "review", "owner", (STREAM,), ROUTE,
                            "forecast.review_decided", 1, "review_result", 1)
    key = CheckpointKey("public", "review", STREAM)
    configure_subscription(SubscriptionChange("create", spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime, context=context)

    with closing(sqlite3.connect(tmp_path / "forecast.db")) as db:
        db.execute("CREATE TABLE decisions (id TEXT PRIMARY KEY, revision TEXT, decision TEXT)")
        db.execute("CREATE TABLE outbox (id TEXT PRIMARY KEY, revision TEXT, decision TEXT)")
        db.execute("INSERT INTO decisions VALUES ('revoked', 'r1', 'approved')")
        db.execute("INSERT INTO outbox VALUES ('revoked', 'r1', 'approved')")
        db.rollback()
        with db:
            db.execute("INSERT INTO decisions VALUES ('d2', 'r2', 'approved')")
            db.execute("INSERT INTO outbox VALUES ('d2', 'r2', 'approved')")
        observed = tuple(db.execute("SELECT id, revision, decision FROM outbox"))
    records = tuple(record_from_fact(DomainFact(
        "forecast.review_decided", ObjectRef("forecast", "f1", version_id=rev), ident, TIME,
        {"data_version": 1, "forecast_id": "f1", "revision_id": rev, "decision_id": ident,
         "decision_code": decision}, observation_id=ident,
    )) for ident, rev, decision in observed)
    source = _source(tmp_path, records)
    runtime = _runtime(state, source, inbox, catalog, names)
    selected = prepare(PrepareRequest(key), runtime=runtime, context=_context(runtime, source, inbox))
    assert selected.value.prepared == 1
    row, = state.scan_dispatches("public", "review", limit=2)
    assert b'"revision_id":"r2"' in row.intent.envelope_bytes
    assert b'revoked' not in row.intent.envelope_bytes and b'forecast.approved' not in row.intent.envelope_bytes
    authority_changed = _runtime(state, source, inbox, catalog, set(names) - {"decision_code"})
    denied = deliver(DeliverRequest("public", row.intent.dispatch_id), runtime=authority_changed,
                     context=_context(authority_changed, source, inbox))
    assert denied.value.state == "cancelled" and inbox.calls == 0
