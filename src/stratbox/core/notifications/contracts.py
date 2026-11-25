"""Portable subscriptions, structured intents and consumer-bound receipts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.identifiers import safe_token
from stratbox.core.observability import JournalCursor, JournalHead, JournalRecord, StreamKey
from stratbox.core.observability.records.contracts import require_utc


@dataclass(frozen=True, slots=True)
class NotificationRoute:
    consumer_id: str
    route_id: str
    target_id: str

    def __post_init__(self) -> None:
        for value in (self.consumer_id, self.route_id, self.target_id):
            safe_token(value)


Scalar = str | int | bool | None


@dataclass(frozen=True, slots=True)
class FilterCondition:
    field: str
    operator: Literal["eq", "in", "exists"]
    values: tuple[Scalar, ...] = ()

    def __post_init__(self) -> None:
        safe_token(self.field)
        if not isinstance(self.values, tuple) or not all(
            type(value) in {str, int, bool, type(None)} for value in self.values
        ):
            raise ValueError("subscription.filter_invalid")
        if not (
            (self.operator == "eq" and len(self.values) == 1)
            or (self.operator == "in" and 1 <= len(self.values) <= 64)
            or (self.operator == "exists" and not self.values)
        ):
            raise ValueError("subscription.filter_invalid")


@dataclass(frozen=True, slots=True)
class CapabilitySelector:
    """Exact coordinates of journaled capability outputs or completion facts."""
    capability_id: str | None = None
    capability_kind: Literal["command", "operation", "scenario", "cascade"] | None = None
    scope_id: str | None = None
    output_name: str | None = None

    def __post_init__(self):
        if all(value is None for value in (self.capability_id, self.capability_kind, self.scope_id, self.output_name)):
            raise ValueError("subscription.selector_empty")
        if self.capability_id is not None:
            safe_token(self.capability_id)
        if self.output_name is not None:
            safe_token(self.output_name)
        if self.capability_kind is not None and self.capability_kind not in {"command", "operation", "scenario", "cascade"}:
            raise ValueError("subscription.selector_kind_invalid")
        if self.scope_id is not None and (not isinstance(self.scope_id, str) or not self.scope_id
                or len(self.scope_id) > 2048 or any(part in {"", ".", ".."} for part in self.scope_id.split("/"))):
            raise ValueError("subscription.selector_scope_invalid")

    @property
    def fields(self):
        return frozenset(name for name in ("capability_id", "capability_kind", "scope_id", "output_name")
                         if getattr(self, name) is not None)

    def matches(self, data):
        return all(name in data and data[name] == getattr(self, name) for name in self.fields)


@dataclass(frozen=True, slots=True)
class DispatchSelectionEvidence:
    """Minimal immutable coordinates pinned from a verified source record."""
    record_kind: str
    run_id: str | None = None
    capability_id: str | None = None
    capability_kind: str | None = None
    scope_id: str | None = None
    output_name: str | None = None
    effect_id: str | None = None
    identity: ByteIdentity | None = None

    @classmethod
    def from_record(cls, record):
        data = record.payload
        identity = data.get("identity")
        if isinstance(identity, dict) or hasattr(identity, "keys"):
            identity = ByteIdentity(identity["sha256"], identity["size"])
        else:
            identity = None
        return cls(record.kind, record.correlation.run_id,
            *(data.get(name) for name in ("capability_id", "capability_kind", "scope_id", "output_name")),
            data.get("effect_id"), identity)

    def matches(self, selector):
        return selector is None or selector.matches({name: getattr(self, name) for name in selector.fields})


@dataclass(frozen=True, slots=True)
class SubscriptionSpec:
    scope_id: str
    subscription_id: str
    owner_id: str
    streams: tuple[StreamKey, ...]
    route: NotificationRoute
    topic_id: str
    topic_version: int
    projection_id: str
    projection_version: int
    filters: tuple[FilterCondition, ...] = ()
    selector: CapabilitySelector | None = None

    def __post_init__(self) -> None:
        for value in (self.scope_id, self.subscription_id, self.owner_id, self.topic_id, self.projection_id):
            safe_token(value)
        for value in (self.topic_version, self.projection_version):
            if type(value) is not int or value < 1:
                raise ValueError("subscription.version_invalid")
        if (not isinstance(self.streams, tuple) or not 1 <= len(self.streams) <= 64
                or len(set(self.streams)) != len(self.streams)
                or any(key.scope_id != self.scope_id for key in self.streams)):
            raise ValueError("subscription.stream_scope_invalid")
        if (not isinstance(self.filters, tuple) or len(self.filters) > 16
                or any(not isinstance(value, FilterCondition) for value in self.filters)):
            raise ValueError("subscription.filter_invalid")
        if not isinstance(self.route, NotificationRoute):
            raise ValueError("subscription.route_invalid")
        if self.selector is not None and not isinstance(self.selector, CapabilitySelector):
            raise ValueError("subscription.selector_invalid")


@dataclass(frozen=True, slots=True)
class Subscription:
    spec: SubscriptionSpec
    revision: int
    status: Literal["disabled", "active", "retired"]
    changed_at_utc: datetime
    grant_ref: str
    activation: tuple[JournalHead, ...] = ()
    activation_revision: int | None = None

    def __post_init__(self) -> None:
        require_utc(self.changed_at_utc)
        safe_token(self.grant_ref)
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("subscription.version_invalid")
        if self.status not in {"disabled", "active", "retired"}:
            raise ValueError("subscription.status_invalid")
        if self.status == "active" and (
            tuple(head.stream for head in self.activation) != self.spec.streams
            or type(self.activation_revision) is not int
            or not 1 <= self.activation_revision <= self.revision
        ):
            raise ValueError("subscription.activation_invalid")


@dataclass(frozen=True, slots=True)
class AccessRequest:
    action: Literal["configure", "inspect", "prepare", "replay", "accept", "reconcile", "waive", "rebase"]
    actor_id: str
    spec: SubscriptionSpec
    stream: StreamKey | None = None
    record: JournalRecord | None = field(default=None, repr=False)
    source_authority_id: str | None = None
    intent: NotificationIntent | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class AccessDecision:
    state: Literal["allow", "denied", "unknown"]
    fields: frozenset[str] = frozenset()
    metadata: frozenset[str] = frozenset()
    grant_ref: str | None = None
    route_revision: str | None = None
    expires_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        if self.state not in {"allow", "denied", "unknown"}:
            raise ValueError("notification.access_decision_invalid")
        if not isinstance(self.fields, frozenset) or not isinstance(self.metadata, frozenset):
            raise ValueError("notification.access_decision_invalid")
        if len(self.fields) > 512 or len(self.metadata) > 16:
            raise ValueError("notification.access_decision_invalid")
        for name in self.fields | self.metadata:
            safe_token(name)
        for value in (self.grant_ref, self.route_revision):
            if value is not None:
                safe_token(value)
        if self.state == "allow" and self.grant_ref is None:
            raise ValueError("notification.grant_required")
        if self.expires_at_utc is not None:
            require_utc(self.expires_at_utc)


class NotificationAuthority(Protocol):
    def authorize(self, request: AccessRequest) -> AccessDecision: ...


@dataclass(frozen=True, slots=True)
class EventPointer:
    cursor: JournalCursor
    source_authority_id: str
    record_id: str
    record_identity: ByteIdentity
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class NotificationIntent:
    dispatch_id: str
    scope_id: str
    subscription_id: str
    subscription_revision: int
    route: NotificationRoute
    route_revision: str
    event: EventPointer
    event_key_kind: Literal["record", "fact", "transition", "effect"]
    event_key: str
    semantic_identity: ByteIdentity
    topic_id: str
    topic_version: int
    projection_id: str
    projection_version: int
    fields: frozenset[str]
    metadata: frozenset[str]
    grant_ref: str
    prepared_at_utc: datetime
    payload_identity: ByteIdentity
    envelope_bytes: bytes = field(repr=False)
    selection_evidence: DispatchSelectionEvidence | None = None


@dataclass(frozen=True, slots=True)
class HandoffLookup:
    scope_id: str
    dispatch_id: str
    attempt_id: str
    route: NotificationRoute
    route_revision: str
    payload_identity: ByteIdentity
    fence: int


@dataclass(frozen=True, slots=True)
class AdmittedHandoff:
    lookup: HandoffLookup
    intent: NotificationIntent = field(repr=False)
    grant_ref: str
    expires_at_utc: datetime
    subscription_revision: int


@dataclass(frozen=True, slots=True)
class HandoffReceipt:
    """An attempt-bound observation from the receiving authority."""

    dispatch_id: str
    attempt_id: str
    route: NotificationRoute
    route_revision: str
    payload_identity: ByteIdentity
    state: Literal["accepted", "not_accepted", "unknown"]
    observed_at_utc: datetime
    evidence_ref: str | None = field(default=None, repr=False)
    reason_code: str | None = None
    retryable: bool = False
    retry_after_utc: datetime | None = None
    receipt_version: int = 1
    final_rejection: bool = False

    def __post_init__(self) -> None:
        for value in (self.dispatch_id, self.attempt_id, self.route_revision,
                      self.evidence_ref, self.reason_code):
            if value is not None:
                safe_token(value)
        require_utc(self.observed_at_utc)
        if (type(self.receipt_version) is not int or self.receipt_version != 1
                or self.state not in {"accepted", "not_accepted", "unknown"}
                or type(self.retryable) is not bool or type(self.final_rejection) is not bool):
            raise ValueError("notification.receipt_invalid")
        if not isinstance(self.payload_identity, ByteIdentity) or type(self.payload_identity.size) is not int:
            raise ValueError("notification.receipt_invalid")
        if self.state != "not_accepted" and (self.final_rejection or self.retryable or self.retry_after_utc is not None):
            raise ValueError("notification.receipt_invalid")
        if self.retry_after_utc is not None:
            require_utc(self.retry_after_utc)


class NotificationConsumer(Protocol):
    """A bound recipient. A durable inbox also fences and deduplicates acceptance.

    In either method, final_rejection attests the exact attempt was never
    accepted and can no longer be accepted. A lookup of a missing row alone
    cannot attest this. Retryability describes permission for a new attempt.
    """

    def accept(self, handoff: AdmittedHandoff) -> HandoffReceipt: ...

    def lookup(self, query: HandoffLookup) -> HandoffReceipt: ...
