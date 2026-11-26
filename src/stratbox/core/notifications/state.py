"""Atomic subscription cursors and individually retained dispatch intents."""
from __future__ import annotations
from pathlib import Path
from threading import RLock
import json
import sqlite3
from contextlib import contextmanager
from uuid import uuid4

from stratbox.shared.data.values import canonical_tree, restore_tree, fingerprint
from stratbox.core.storage.filestore.types import MutationRejected


class NotificationRejected(MutationRejected, ValueError):
    def __init__(self,code): super().__init__(code,code=code)


def _policy(selector, route):
    return fingerprint((dict(selector or {}), route))


def _intent(fact, subscription_id, policy, route):
    payload = dict(kind=fact.kind, run_id=fact.run_id, scope_id=fact.scope_id,
        command_id=fact.command_id, output_name=fact.output_name, fact_sequence=fact.sequence,
        data=dict(fact.data),stream_id=fact.stream_id)
    return {"id":fingerprint((subscription_id, policy, fact.stream_id, fact.run_id, fact.sequence)),
        "subscription_id":subscription_id, "route":route, "payload":payload}


def _selected(fact, selector):
    if fact.data.get("origin") == "notification" and dict(selector or {}).get("origin") != "notification": return False
    return all(getattr(fact, key, fact.data.get(key)) == value for key,value in dict(selector or {}).items())


def _stream(facts, previous=None):
    streams = {fact.stream_id for fact in facts}
    if len(streams) > 1 or streams and not next(iter(streams)):
        raise NotificationRejected("notification.mixed_or_unknown_fact_stream")
    stream = next(iter(streams),previous)
    if previous is not None and stream != previous:
        raise NotificationRejected("notification.journal_stream_changed")
    return stream


class MemoryNotificationState:
    provider_id = "notifications.memory"
    def __init__(self, capacity=10000):
        if type(capacity) is not int or capacity < 1: raise NotificationRejected("notification.invalid_capacity")
        self.capacity, self._lock, self._subscriptions = capacity, RLock(), {}
        self.scope_id = uuid4().hex

    def prepare(self, facts, *, subscription_id="default", selector=None, route=None):
        facts = tuple(facts)
        if len(facts) > self.capacity: raise NotificationRejected("notification.page_limit")
        policy = _policy(selector, route)
        with self._lock:
            previous = self._subscriptions.get(subscription_id)
            if previous is None and len(self._subscriptions) >= self.capacity:
                raise NotificationRejected("notification.subscription_capacity_exhausted")
            if previous is not None and previous["policy"] != policy:
                raise NotificationRejected("notification.policy_changed_requires_new_subscription")
            stream = _stream(facts,previous.get("stream") if previous else None)
            state = previous or {"policy":policy,"cursor":0,"intents":{}}
            cursor, intents, selected = state["cursor"], dict(state["intents"]), []
            for fact in sorted(facts,key=lambda fact:fact.sequence):
                if fact.sequence <= cursor: continue
                if _selected(fact, selector):
                    intent = _intent(fact, subscription_id, policy, route)
                    intents.setdefault(intent["id"], intent); selected.append(intent)
                cursor = max(cursor, fact.sequence)
            occupied = sum(len(value["intents"]) for key,value in self._subscriptions.items() if key != subscription_id)
            if occupied + len(intents) > self.capacity: raise NotificationRejected("notification.capacity_exhausted")
            self._subscriptions[subscription_id] = {"policy":policy,"cursor":cursor,"intents":intents,"stream":stream}
            return tuple(selected)

    def pending(self, subscription_id="default", *, after_sequence=0, limit=1000):
        if after_sequence < 0 or not 0 < limit <= 10000: raise NotificationRejected("notification.invalid_page")
        with self._lock:
            state = self._subscriptions.get(subscription_id)
            return () if state is None else tuple(sorted((item for item in state["intents"].values()
                if item["payload"]["fact_sequence"] > after_sequence),
                key=lambda item:(item["payload"]["fact_sequence"],item["id"])))[:limit]

    def acknowledge(self, subscription_id, intent_id, receipt):
        _confirmed_intent(intent_id,receipt)
        with self._lock:
            state = self._subscriptions.get(subscription_id)
            removed = state is not None and state["intents"].pop(intent_id,None) is not None
            return {"removed":bool(removed),"intent_id":intent_id}


class FileNotificationState:
    """A bounded page transaction advances its cursor with every selected intent."""
    provider_id = "notifications.sqlite"
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True,exist_ok=True)
        self._lock = RLock()
        self._database = self.directory / "dispatch.sqlite"
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO state_identity VALUES ('identity',?)",(uuid4().hex,))
            self.scope_id = db.execute("SELECT value FROM state_identity WHERE key='identity'").fetchone()[0]
            db.execute("CREATE TABLE IF NOT EXISTS subscriptions (id TEXT PRIMARY KEY, policy TEXT NOT NULL, cursor INTEGER NOT NULL, stream TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS intents (id TEXT PRIMARY KEY, subscription TEXT NOT NULL, sequence INTEGER NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS intents_page ON intents(subscription, sequence, id)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self._database,timeout=30)
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db: yield db
        finally:
            db.close()

    def prepare(self, facts, *, subscription_id="default", selector=None, route=None):
        facts = tuple(facts)
        if len(facts) > 10000: raise NotificationRejected("notification.page_limit")
        policy = _policy(selector,route)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT policy,cursor,stream FROM subscriptions WHERE id=?",(subscription_id,)).fetchone()
            if previous is not None and previous[0] != policy:
                raise NotificationRejected("notification.policy_changed_requires_new_subscription")
            stream = _stream(facts,previous[2] if previous else None)
            cursor, selected = previous[1] if previous else 0, []
            for fact in sorted(facts,key=lambda fact:fact.sequence):
                if fact.sequence <= cursor: continue
                if _selected(fact,selector):
                    intent = _intent(fact,subscription_id,policy,route)
                    raw = json.dumps(canonical_tree(intent),sort_keys=True,separators=(",",":"))
                    db.execute("INSERT OR IGNORE INTO intents VALUES (?,?,?,?)",(intent["id"],subscription_id,fact.sequence,raw))
                    selected.append(intent)
                cursor = max(cursor,fact.sequence)
            db.execute("INSERT INTO subscriptions VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET cursor=excluded.cursor,stream=excluded.stream",
                (subscription_id,policy,cursor,stream))
            return tuple(selected)

    def pending(self, subscription_id="default", *, after_sequence=0, limit=1000):
        if after_sequence < 0 or not 0 < limit <= 10000: raise NotificationRejected("notification.invalid_page")
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT payload FROM intents WHERE subscription=? AND sequence>? ORDER BY sequence,id LIMIT ?",
                (subscription_id,after_sequence,limit)).fetchall()
            return tuple(restore_tree(json.loads(row[0])) for row in rows)

    def acknowledge(self, subscription_id, intent_id, receipt):
        _confirmed_intent(intent_id,receipt)
        with self._lock, self._connect() as db:
            cursor = db.execute("DELETE FROM intents WHERE subscription=? AND id=?",(subscription_id,intent_id))
            return {"removed":bool(cursor.rowcount),"intent_id":intent_id}


def _confirmed_intent(intent_id,receipt):
    if (getattr(receipt,"effect_id",None) != intent_id or getattr(receipt,"status",None) != "confirmed"
            or getattr(receipt,"kind",None) != "notification.deliver"):
        raise NotificationRejected("notification.confirmed_matching_receipt_required")
