"""Atomic in-memory notification state implementation for local sessions."""
from __future__ import annotations
from threading import RLock
from stratbox.shared.data import ByteIdentity
from stratbox.core.observability import JournalCursor, JournalRecord, JournalWriteReceipt, encode_record
from stratbox.core.notifications.contracts import Subscription
from stratbox.core.notifications.state.contracts import (AuditBatch, CheckpointKey, Dispatch, Replay, StateMutation,
    StateReceipt, PENDING_STATES, DISPATCH_STATES)

class MemoryNotificationState:
    """Atomic reference store for local sessions and provider contract tests."""

    durable = False

    def __init__(self, *, max_pending: int = 2000, max_entries: int = 100_000):
        if any(type(n) is not int or n < 1 for n in (max_pending, max_entries)):
            raise ValueError("notification.state_limits_invalid")
        self._max_pending, self._max_entries = max_pending, max_entries
        self._lock = RLock()
        self._subscriptions: dict[tuple[str, str], Subscription] = {}
        self._revisions: dict[tuple[str, str, int], Subscription] = {}
        self._checkpoints: dict[CheckpointKey, JournalCursor] = {}
        self._dispatches: dict[tuple[str, str], Dispatch] = {}
        self._dispatch_index: dict[tuple[str, str], list[str]] = {}
        self._replays: dict[CheckpointKey, Replay] = {}
        self._records: dict[tuple[str, str, str], ByteIdentity] = {}
        self._commands: dict[tuple[str, str], StateReceipt] = {}
        self._audit: dict[tuple[str, str], JournalRecord] = {}
        self._pending: dict[tuple[str, str], int] = {}

    def get_subscription(self, scope_id: str, subscription_id: str) -> Subscription | None:
        with self._lock:
            return self._subscriptions.get((scope_id, subscription_id))

    def get_revision(self, scope_id: str, subscription_id: str, revision: int) -> Subscription | None:
        with self._lock:
            return self._revisions.get((scope_id, subscription_id, revision))

    def get_checkpoint(self, key: CheckpointKey) -> JournalCursor | None:
        with self._lock:
            return self._checkpoints.get(key)

    def get_dispatch(self, scope_id: str, dispatch_id: str) -> Dispatch | None:
        with self._lock:
            return self._dispatches.get((scope_id, dispatch_id))

    def get_replay(self, key: CheckpointKey) -> Replay | None:
        with self._lock:
            return self._replays.get(key)

    def get_record_identity(self, scope_id: str, source_authority_id: str, record_id: str) -> ByteIdentity | None:
        with self._lock:
            return self._records.get((scope_id, source_authority_id, record_id))

    def scan_dispatches(
        self, scope_id: str, subscription_id: str, *, limit: int, after: int = 0,
    ) -> tuple[Dispatch, ...]:
        if type(limit) is not int or not 1 <= limit <= 100_001:
            raise ValueError("notification.scan_limit_invalid")
        if type(after) is not int or after < 0:
            raise ValueError("notification.scan_cursor_invalid")
        with self._lock:
            keys = self._dispatch_index.get((scope_id, subscription_id), ())
            return tuple(self._dispatches[(scope_id, key)] for key in keys[after:after + limit])

    def lookup_command(self, scope_id: str, command_id: str) -> StateReceipt | None:
        with self._lock:
            return self._commands.get((scope_id, command_id))

    def pending_audit(self, scope_id: str, *, limit: int) -> tuple[JournalRecord, ...]:
        if type(limit) is not int or not 1 <= limit <= 10_000:
            raise ValueError("notification.audit_limit_invalid")
        entries = []
        with self._lock:
            for (scope, _), record in self._audit.items():
                if scope == scope_id:
                    entries.append(record)
                    if len(entries) == limit:
                        break
        return tuple(entries)

    def acknowledge_audit(self, batch: AuditBatch, receipt: JournalWriteReceipt) -> None:
        if not batch.is_confirmed_by(receipt):
            raise ValueError("notification.audit_unconfirmed")
        with self._lock:
            for record in batch.records:
                pending = self._audit.get((batch.scope_id, record.record_id))
                if pending is not None and encode_record(pending) != encode_record(record):
                    raise ValueError("notification.audit_conflict")
            for record_id in batch.record_ids:
                self._audit.pop((batch.scope_id, record_id), None)

    def _check(self, command: StateMutation) -> tuple[str, str] | None:
        key = command.scope_id, command.subscription_id
        current = self._subscriptions.get(key)
        if (current.revision if current else None) != command.expected_revision:
            return "conflict", "subscription.revision_conflict"
        if command.subscription is not None and (
            (command.subscription.spec.scope_id, command.subscription.spec.subscription_id) != key
            or command.subscription.revision != (command.expected_revision or 0) + 1
        ):
            return "rejected", "subscription.revision_invalid"
        for update in command.checkpoint_updates:
            if ((update.key.scope_id, update.key.subscription_id) != key
                    or update.key.stream != update.value.stream or self._checkpoints.get(update.key) != update.expected):
                return "conflict", "notification.checkpoint_conflict"
        if command.replay is not None and (
            (command.replay.key.scope_id, command.replay.key.subscription_id) != key
            or command.replay.key in self._replays
        ):
            return "conflict", "notification.replay_conflict"
        pending_delta = 0
        for update in command.dispatch_updates:
            value = update.value
            intent = value.intent
            previous = self._dispatches.get((command.scope_id, intent.dispatch_id))
            if (previous.version if previous else None) != update.expected_version:
                return "conflict", "notification.dispatch_conflict"
            if ((intent.scope_id, intent.subscription_id) != key
                    or value.state not in DISPATCH_STATES
                    or value.version != (update.expected_version or 0) + 1
                    or (previous is not None and previous.intent != intent)):
                return "rejected", "notification.dispatch_invalid"
            pending_delta += int(value.state in PENDING_STATES) - int(
                previous is not None and previous.state in PENDING_STATES)
        if self._pending.get(key, 0) + pending_delta > self._max_pending:
            return "rejected", "notification.queue_capacity"
        for record in command.record_identities:
            previous = self._records.get((command.scope_id, record.source_authority_id, record.record_id))
            if previous is not None and previous != record.identity:
                return "conflict", "journal.record_identity_conflict"
        for record in command.audit:
            previous = self._audit.get((command.scope_id, record.record_id))
            if previous is not None and encode_record(previous) != encode_record(record):
                return "conflict", "notification.audit_conflict"
        if len(self._audit) + len(command.audit) > self._max_entries:
            return "rejected", "notification.audit_capacity"
        counts = (
            len(self._commands), len(self._revisions), len(self._dispatches) + len(command.dispatch_updates),
            len(self._audit) + len(command.audit), len(self._records) + len(command.record_identities),
        )
        # Existing work can still be finished when the new-work budget is exhausted.
        creates_work = bool(command.record_identities or command.subscription or command.replay
                            or any(update.expected_version is None for update in command.dispatch_updates))
        if creates_work and max(counts) >= self._max_entries:
            return "rejected", "notification.state_capacity"
        return None

    def commit(self, mutation: StateMutation) -> StateReceipt:
        scope, sub_id, command_id = mutation.scope_id, mutation.subscription_id, mutation.command_id
        with self._lock:
            previous = self._commands.get((scope, command_id))
            if previous is not None:
                return previous
            failure = self._check(mutation)
            if failure is not None:
                return StateReceipt(command_id, *failure)
            key = scope, sub_id
            if mutation.subscription is not None:
                self._subscriptions[key] = mutation.subscription
                self._revisions[(*key, mutation.subscription.revision)] = mutation.subscription
            for update in mutation.checkpoint_updates:
                self._checkpoints[update.key] = update.value
            for update in mutation.dispatch_updates:
                dispatch_id = update.value.intent.dispatch_id
                previous_row = self._dispatches.get((scope, dispatch_id))
                if previous_row is None:
                    self._dispatch_index.setdefault(key, []).append(dispatch_id)
                self._pending[key] = self._pending.get(key, 0) + int(
                    update.value.state in PENDING_STATES) - int(
                    previous_row is not None and previous_row.state in PENDING_STATES)
                self._dispatches[(scope, dispatch_id)] = update.value
            for record in mutation.record_identities:
                self._records[scope, record.source_authority_id, record.record_id] = record.identity
            for record in mutation.audit:
                self._audit[(scope, record.record_id)] = record
            if mutation.replay is not None:
                self._replays[mutation.replay.key] = mutation.replay
            receipt = StateReceipt(command_id, "confirmed")
            self._commands[(scope, command_id)] = receipt
            return receipt


