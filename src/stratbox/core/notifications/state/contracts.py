"""Transactional state required by resumable notifications."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import datetime
from threading import RLock
from typing import Literal, Protocol

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution.contracts import safe_token
from stratbox.core.observability import (
    JournalCursor, JournalHead, JournalRecord, JournalWriteReceipt, RecordWriter, StreamKey,
    encode_record, encode_records,
)
from stratbox.core.observability.journal.codecs import MAX_SEGMENT_BYTES
from stratbox.core.observability.records.contracts import require_utc

from stratbox.core.notifications.contracts import HandoffLookup, HandoffReceipt, NotificationIntent, Subscription

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
    evidence_problem: str | None = None


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
    if isinstance(value, JournalRecord):
        value = encode_record(value)
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


def _require_unique(items: tuple, key: Callable, code: str) -> None:
    if type(items) is not tuple:
        raise ValueError("notification.mutation_items_invalid")
    if len({key(item) for item in items}) != len(items):
        raise ValueError(code)


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
        _require_unique(self.checkpoint_updates, lambda item: item.key, "notification.checkpoint_duplicate")
        _require_unique(self.dispatch_updates, lambda item: item.value.intent.dispatch_id,
                        "notification.dispatch_duplicate")
        _require_unique(self.record_identities, lambda item: (item.source_authority_id, item.record_id),
                        "journal.record_identity_duplicate")
        _require_unique(self.audit, lambda item: item.record_id, "notification.audit_duplicate")
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


@dataclass(frozen=True, slots=True)
class AuditBatch:
    """The exact ordered obligations sent to a journal writer for one scope."""

    scope_id: str
    records: tuple[JournalRecord, ...] = field(repr=False)
    format: str
    record_ids: tuple[str, ...] = field(init=False)
    content_identity: ByteIdentity = field(init=False)
    segment_id: str = field(init=False)

    def __post_init__(self) -> None:
        safe_token(self.scope_id)
        if type(self.records) is not tuple or not 1 <= len(self.records) <= 10_000:
            raise ValueError("notification.audit_batch_invalid")
        _require_unique(self.records, lambda record: record.record_id, "notification.audit_duplicate")
        identity = ByteIdentity.of(encode_records(self.records, format=self.format, max_bytes=MAX_SEGMENT_BYTES))
        object.__setattr__(self, "record_ids", tuple(record.record_id for record in self.records))
        object.__setattr__(self, "content_identity", identity)
        object.__setattr__(self, "segment_id", ByteIdentity.of(canonical_manifest_bytes({
            "scope_id": self.scope_id, "content_sha256": identity.sha256,
        })).sha256)

    def is_confirmed_by(self, receipt: JournalWriteReceipt) -> bool:
        return isinstance(receipt, JournalWriteReceipt) and receipt.confirms_batch(
            self.content_identity, self.record_ids, segment_id=self.segment_id,
        )


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
        """Compare each unique key and commit all changes with exact audit obligations.

        A durable provider's confirmation covers both state and pending audit
        across restarts. Lookups confirm the same command identity.
        """
        ...

    def lookup_command(self, scope_id: str, command_id: str) -> StateReceipt | None: ...

    def pending_audit(self, scope_id: str, *, limit: int) -> tuple[JournalRecord, ...]:
        """Return exact unacknowledged records in a stable order for this scope."""
        ...

    def acknowledge_audit(self, batch: AuditBatch, receipt: JournalWriteReceipt) -> None:
        """Require exact batch confirmation and compare pending bytes before atomic removal.

        An already-cleared entry is idempotent. A conflicting current entry
        prevents removal of any part of the batch.
        """
        ...
