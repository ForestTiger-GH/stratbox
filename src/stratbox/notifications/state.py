"""Transactional state required by resumable notifications."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from threading import RLock
from typing import Literal, Protocol

from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution.contracts import safe_token
from stratbox.observability import (
    JournalCursor, JournalHead, JournalRecord, JournalWriteReceipt, RecordWriter, StreamKey,
)
from stratbox.observability.contracts import require_utc

from .contracts import HandoffLookup, HandoffReceipt, NotificationIntent, Subscription

DispatchState = Literal[
    "ready", "in_flight", "retry_due", "consumer_accepted", "rejected",
    "unknown", "cancelled", "expired", "quarantined",
]
PENDING_STATES = frozenset({"ready", "in_flight", "retry_due", "unknown"})
DISPATCH_STATES = PENDING_STATES | {
    "consumer_accepted", "rejected", "cancelled", "expired", "quarantined",
}


@dataclass(frozen=True, slots=True)
class CheckpointKey:
    scope_id: str
    subscription_id: str
    stream: StreamKey
    replay_id: str | None = None

    def __post_init__(self) -> None:
        safe_token(self.scope_id)
        safe_token(self.subscription_id)
        if self.replay_id is not None:
            safe_token(self.replay_id)
        if self.scope_id != self.stream.scope_id:
            raise ValueError("subscription.stream_scope_invalid")


@dataclass(frozen=True, slots=True)
class Replay:
    key: CheckpointKey
    head: JournalHead
    first_offset: int
    last_offset: int
    expires_at_utc: datetime
    grant_ref: str

    def __post_init__(self) -> None:
        require_utc(self.expires_at_utc)
        safe_token(self.grant_ref)
        if (self.key.replay_id is None or self.key.stream != self.head.stream
                or type(self.first_offset) is not int or type(self.last_offset) is not int
                or not self.head.first_retained <= self.first_offset <= self.last_offset <= self.head.tail_offset
                or self.last_offset - self.first_offset >= 1000):
            raise ValueError("notification.replay_range_invalid")


@dataclass(frozen=True, slots=True)
class Attempt:
    lookup: HandoffLookup
    number: int
    owner_id: str
    started_at_utc: datetime
    claim_until_utc: datetime
    subscription_revision: int
    receipt: HandoffReceipt | None = None


@dataclass(frozen=True, slots=True)
class Dispatch:
    intent: NotificationIntent
    version: int = 1
    state: DispatchState = "ready"
    attempts: tuple[Attempt, ...] = ()
    next_due_at_utc: datetime | None = None
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class RecordIdentity:
    source_authority_id: str
    record_id: str
    identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class CheckpointUpdate:
    key: CheckpointKey
    expected: JournalCursor | None
    value: JournalCursor


@dataclass(frozen=True, slots=True)
class DispatchUpdate:
    expected_version: int | None
    value: Dispatch


def _canonical(value):
    if isinstance(value, bytes):
        return {"sha256": ByteIdentity.of(value).sha256, "size": len(value)}
    if is_dataclass(value):
        return {item.name: _canonical(getattr(value, item.name))
                for item in fields(value) if item.name != "command_id"}
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, Mapping):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class StateMutation:
    scope_id: str
    subscription_id: str
    expected_revision: int | None
    subscription: Subscription | None = None
    checkpoint_updates: tuple[CheckpointUpdate, ...] = ()
    dispatch_updates: tuple[DispatchUpdate, ...] = ()
    record_identities: tuple[RecordIdentity, ...] = ()
    audit: tuple[JournalRecord, ...] = ()
    replay: Replay | None = None
    command_id: str = field(init=False)

    def __post_init__(self) -> None:
        safe_token(self.scope_id)
        safe_token(self.subscription_id)
        object.__setattr__(self, "command_id", ByteIdentity.of(canonical_manifest_bytes({
            "mutation_version": 1, "mutation": _canonical(self),
        })).sha256)


@dataclass(frozen=True, slots=True)
class StateReceipt:
    command_id: str
    state: Literal["confirmed", "conflict", "rejected", "unknown"]
    reason_code: str | None = None

    def __post_init__(self) -> None:
        safe_token(self.command_id)
        if self.reason_code is not None:
            safe_token(self.reason_code)
        if self.state not in {"confirmed", "conflict", "rejected", "unknown"}:
            raise ValueError("notification.state_receipt_invalid")


class NotificationStateReader(Protocol):
    durable: bool

    def get_subscription(self, scope_id: str, subscription_id: str) -> Subscription | None: ...

    def get_revision(self, scope_id: str, subscription_id: str, revision: int) -> Subscription | None: ...

    def get_checkpoint(self, key: CheckpointKey) -> JournalCursor | None: ...

    def get_dispatch(self, scope_id: str, dispatch_id: str) -> Dispatch | None: ...

    def get_replay(self, key: CheckpointKey) -> Replay | None: ...

    def get_record_identity(self, scope_id: str, source_authority_id: str, record_id: str) -> ByteIdentity | None: ...

    def scan_dispatches(
        self, scope_id: str, subscription_id: str, *, limit: int, after: int = 0,
    ) -> tuple[Dispatch, ...]: ...


class NotificationStateStore(NotificationStateReader, Protocol):
    def commit(self, mutation: StateMutation) -> StateReceipt:
        """Atomically compare expected rows and commit the mutation with its audit."""
        ...

    def lookup_command(self, scope_id: str, command_id: str) -> StateReceipt | None: ...

    def pending_audit(self, scope_id: str, *, limit: int) -> tuple[JournalRecord, ...]: ...

    def acknowledge_audit(self, scope_id: str, receipt: JournalWriteReceipt) -> None: ...


def commit_and_lookup(store: NotificationStateStore, mutation: StateMutation) -> StateReceipt:
    try:
        receipt = store.commit(mutation)
    except Exception:
        receipt = None
    if (isinstance(receipt, StateReceipt) and receipt.command_id == mutation.command_id
            and receipt.state in {"confirmed", "conflict", "rejected"}):
        return receipt
    try:
        recovered = store.lookup_command(mutation.scope_id, mutation.command_id)
    except Exception:
        recovered = None
    if (isinstance(recovered, StateReceipt) and recovered.state == "confirmed"
            and recovered.command_id == mutation.command_id):
        return recovered
    return StateReceipt(mutation.command_id, "unknown", "notification.state_commit_unknown")


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

    def acknowledge_audit(self, scope_id: str, receipt: JournalWriteReceipt) -> None:
        if receipt.state != "confirmed":
            raise ValueError("notification.audit_unconfirmed")
        with self._lock:
            for record_id in receipt.record_ids:
                self._audit.pop((scope_id, record_id), None)

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
            if previous is not None and previous != record:
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


def flush_audit(
    state: NotificationStateStore, scope_id: str, writer: RecordWriter, *, limit: int = 200,
) -> JournalWriteReceipt | None:
    records = state.pending_audit(scope_id, limit=limit)
    if not records:
        return None
    from stratbox.observability import encode_record

    segment_id = ByteIdentity.of(canonical_manifest_bytes({
        "scope": scope_id, "identities": [ByteIdentity.of(encode_record(record)).sha256 for record in records],
    })).sha256
    receipt = writer.write_batch(records, segment_id=segment_id)
    if receipt.state == "confirmed" and receipt.record_ids == tuple(record.record_id for record in records):
        state.acknowledge_audit(scope_id, receipt)
    return receipt
