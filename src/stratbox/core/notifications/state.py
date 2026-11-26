"""Atomic cursor/intent state with deterministic idempotent dispatch identity."""
from __future__ import annotations
from pathlib import Path
from threading import RLock
from hashlib import sha256
import json
import os
import tempfile

from stratbox.shared.data.values import canonical_tree, restore_tree, fingerprint


class MemoryNotificationState:
    def __init__(self):
        self._lock, self._subscriptions = RLock(), {}

    def _read(self, subscription_id):
        return self._subscriptions.get(subscription_id)

    def _write(self, subscription_id, record):
        self._subscriptions[subscription_id] = record

    def prepare(self, facts, *, subscription_id="default", selector=None, route=None):
        selector = dict(selector or {})
        policy = fingerprint((selector, route))
        with self._lock:
            previous = self._read(subscription_id)
            if previous is not None and previous["policy"] != policy:
                raise ValueError("notification.policy_changed_requires_new_subscription")
            state = previous or {"policy": policy, "cursor": 0, "intents": {}}
            intents = dict(state["intents"])
            cursor = state["cursor"]
            selected = []
            for fact in sorted(facts, key=lambda fact: fact.sequence):
                if fact.sequence <= cursor:
                    continue
                if all(getattr(fact, key, fact.data.get(key)) == value for key, value in selector.items()):
                    intent_id = fingerprint((subscription_id, policy, fact.run_id, fact.sequence))
                    payload = dict(kind=fact.kind, run_id=fact.run_id, scope_id=fact.scope_id,
                        command_id=fact.command_id, output_name=fact.output_name, fact_sequence=fact.sequence,
                        data=dict(fact.data))
                    intent = {"id": intent_id, "subscription_id": subscription_id, "route": route, "payload": payload}
                    intents.setdefault(intent_id, intent)
                    selected.append(intents[intent_id])
                cursor = max(cursor, fact.sequence)
            self._write(subscription_id, {"policy": policy, "cursor": cursor, "intents": intents})
            return tuple(selected)

    def pending(self, subscription_id="default"):
        with self._lock:
            state = self._read(subscription_id)
            return () if state is None else tuple(sorted(state["intents"].values(),
                key=lambda item: (item["payload"]["fact_sequence"], item["id"])))


class FileNotificationState(MemoryNotificationState):
    def __init__(self, directory):
        super().__init__()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, subscription_id):
        digest = sha256(subscription_id.encode()).hexdigest()
        parent = self.directory / digest[:2]
        parent.mkdir(exist_ok=True)
        return parent / (digest + ".json")

    def _read(self, subscription_id):
        path = self._path(subscription_id)
        return restore_tree(json.loads(path.read_bytes())) if path.exists() else None

    def _write(self, subscription_id, record):
        path = self._path(subscription_id)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".intent-")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(json.dumps(canonical_tree(record), sort_keys=True, separators=(",", ":")).encode())
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
