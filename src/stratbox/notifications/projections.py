"""Bounded operational views and independent evidence of downstream delivery."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal

from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution import ExecutionContext, OperationFailure
from stratbox.execution.contracts import safe_token
from stratbox.observability import JournalCursor, JournalHead, JournalRecord
from stratbox.observability.contracts import require_utc

from .audit import audit_record
from .contracts import SubscriptionSpec
from .runtime import NotificationReadRuntime, access, need_access, require_admission
from .state import CheckpointKey, DISPATCH_STATES, PENDING_STATES
from .subscriptions import _head


@dataclass(frozen=True, slots=True)
class TopicAvailability:
    topic_id: str
    topic_version: int
    projection_id: str
    projection_version: int
    fields: tuple[str, ...]
    filter_fields: tuple[str, ...]


def accessible_topics(
    scope: SubscriptionSpec, *, reader: NotificationReadRuntime, context: ExecutionContext | None = None,
) -> tuple[TopicAvailability, ...]:
    """Discover topic projections for one proposed source scope and route."""
    context = context or ExecutionContext()
    require_admission(reader, context, scope.scope_id)
    bindings = tuple(reader.source_for(stream) for stream in scope.streams)
    for binding in bindings:
        require_admission(reader, context, scope.scope_id, binding)
    results = []
    for topic in reader.catalog.definitions():
        if not all(topic.in_scope(binding.source_authority_id) for binding in bindings):
            continue
        for projection in topic.projections:
            spec = replace(scope, topic_id=topic.topic_id, topic_version=topic.version, filters=(),
                           projection_id=projection.projection_id, projection_version=projection.version)
            grants = tuple(access(reader, "inspect", spec, context.clock.now(), stream=binding.stream,
                                  authority_id=binding.source_authority_id) for binding in bindings)
            if any(grant.state != "allow" for grant in grants):
                continue
            visible = set.intersection(*(set(grant.fields) for grant in grants))
            if any(rule.required and rule.name not in visible for rule in projection.fields):
                continue
            fields = tuple(rule.name for rule in projection.fields if rule.name in visible)
            results.append(TopicAvailability(
                topic.topic_id, topic.version, projection.projection_id, projection.version,
                fields, tuple(sorted(topic.filter_fields.intersection(fields))),
            ))
    return tuple(results)


@dataclass(frozen=True, slots=True)
class DispatchStatus:
    dispatch_id: str
    state: str
    attempt_id: str | None
    attempts: int
    due_at_utc: datetime | None
    reason_code: str | None
    source_record_id: str | None
    evidence_problem: str | None


@dataclass(frozen=True, slots=True)
class NotificationHealth:
    subscription_revision: int
    subscription_status: str
    head: JournalHead
    cursor_lag_positions: int | None
    counts_by_state: tuple[tuple[str, int], ...]
    oldest_pending_age_seconds: int | None
    oldest_unknown_age_seconds: int | None
    scanned: int
    truncated: bool
    due: tuple[DispatchStatus, ...]
    unresolved: tuple[DispatchStatus, ...]
    next_scan_after: int | None
    oldest_pending_source_positions: tuple[JournalCursor, ...]


def notification_health(
    key: CheckpointKey, *, reader: NotificationReadRuntime, context: ExecutionContext | None = None,
    limit: int = 200, max_due: int = 50, after_position: int = 0,
) -> NotificationHealth:
    if (type(limit) is not int or not 1 <= limit <= 10_000
            or type(max_due) is not int or not 1 <= max_due <= 50):
        raise ValueError("notification.scan_limit_invalid")
    context = context or ExecutionContext()
    binding = reader.source_for(key.stream)
    require_admission(reader, context, key.scope_id, binding)
    sub = reader.state.get_subscription(key.scope_id, key.subscription_id)
    if sub is None or key.stream not in sub.spec.streams:
        raise OperationFailure("subscription.not_found")
    now = context.clock.now()
    grant = access(reader, "inspect", sub.spec, now, stream=key.stream,
                   authority_id=binding.source_authority_id)
    need_access(grant)
    head = _head(binding)
    cursor = reader.state.get_checkpoint(key)
    lag = None
    target = head.tail_offset
    if key.replay_id is not None:
        replay = reader.state.get_replay(key)
        if replay is None:
            raise OperationFailure("notification.replay_unavailable")
        head, target = replay.head, replay.last_offset
    if cursor is not None and cursor.epoch_id == head.epoch_id and head.first_retained - 1 <= cursor.last_offset <= target:
        lag = target - cursor.last_offset
    rows = reader.state.scan_dispatches(key.scope_id, key.subscription_id, limit=limit + 1, after=after_position)
    counts: Counter[str] = Counter()
    oldest_pending = oldest_unknown = None
    due: list[DispatchStatus] = []
    unresolved: list[DispatchStatus] = []
    oldest_positions: dict[str, JournalCursor] = {}
    for row in rows[:limit]:
        intent = row.intent
        if intent.event.cursor.stream != key.stream or row.state not in DISPATCH_STATES:
            continue
        visible = access(reader, "inspect", sub.spec, now, stream=key.stream,
                         authority_id=binding.source_authority_id, intent=intent)
        if visible.state != "allow":
            continue
        counts[row.state] += 1
        age = max(0, int((now - intent.prepared_at_utc).total_seconds()))
        if row.state in PENDING_STATES:
            oldest_pending = age if oldest_pending is None else max(oldest_pending, age)
            position = intent.event.cursor
            if "event_ref" in visible.metadata:
                oldest = oldest_positions.get(position.epoch_id)
                if oldest is None or position.last_offset < oldest.last_offset:
                    oldest_positions[position.epoch_id] = position
        last = row.attempts[-1] if row.attempts else None
        status = DispatchStatus(
            intent.dispatch_id, row.state, last.lookup.attempt_id if last else None, len(row.attempts),
            row.next_due_at_utc, row.reason_code,
            intent.event.record_id if "event_ref" in visible.metadata else None,
            row.evidence_problem,
        )
        if row.state == "unknown" or (row.state == "in_flight" and last and now >= last.claim_until_utc):
            elapsed = max(0, int((now - last.started_at_utc).total_seconds())) if last else age
            oldest_unknown = elapsed if oldest_unknown is None else max(oldest_unknown, elapsed)
            unresolved.append(status)
        if row.state == "ready" or (
            row.state == "retry_due" and row.next_due_at_utc is not None and row.next_due_at_utc <= now
        ):
            due.append(status)
    due.sort(key=lambda row: (row.due_at_utc is not None, row.due_at_utc, row.dispatch_id))
    return NotificationHealth(
        sub.revision, sub.status, head, lag, tuple(sorted(counts.items())),
        oldest_pending, oldest_unknown, sum(counts.values()), len(rows) > limit,
        tuple(due[:max_due]), tuple(unresolved[:max_due]),
        after_position + limit if len(rows) > limit else None,
        tuple(oldest_positions[epoch] for epoch in sorted(oldest_positions)),
    )


def inspect_dispatch(
    scope_id: str, dispatch_id: str, *, reader: NotificationReadRuntime,
    context: ExecutionContext | None = None,
) -> DispatchStatus:
    context = context or ExecutionContext()
    require_admission(reader, context, scope_id)
    row = reader.state.get_dispatch(scope_id, dispatch_id)
    if row is None:
        raise OperationFailure("notification.dispatch_not_found")
    sub = reader.state.get_subscription(scope_id, row.intent.subscription_id)
    if sub is None:
        raise OperationFailure("subscription.not_found")
    grant = access(reader, "inspect", sub.spec, context.clock.now(),
                   stream=row.intent.event.cursor.stream,
                   authority_id=row.intent.event.source_authority_id, intent=row.intent)
    if grant.state == "denied":
        raise OperationFailure("notification.dispatch_not_found")
    need_access(grant)
    return DispatchStatus(
        dispatch_id, row.state, row.attempts[-1].lookup.attempt_id if row.attempts else None,
        len(row.attempts), row.next_due_at_utc, row.reason_code,
        row.intent.event.record_id if "event_ref" in grant.metadata else None,
        row.evidence_problem,
    )


@dataclass(frozen=True, slots=True)
class ExternalDeliveryReceipt:
    """A stage reported by the owner of the downstream effect."""

    scope_id: str
    dispatch_id: str
    attempt_id: str
    consumer_id: str
    stage: Literal["transport_accepted", "delivered", "read"]
    state: Literal["confirmed", "failed", "unknown"]
    observed_at_utc: datetime
    evidence_ref: str | None = field(default=None, repr=False)
    reason_code: str | None = None

    def __post_init__(self) -> None:
        for token in (self.scope_id, self.dispatch_id, self.attempt_id, self.consumer_id,
                      self.evidence_ref, self.reason_code):
            if token is not None:
                safe_token(token)
        require_utc(self.observed_at_utc)
        if self.stage not in {"transport_accepted", "delivered", "read"} or self.state not in {
            "confirmed", "failed", "unknown",
        }:
            raise ValueError("notification.external_receipt_invalid")
        if self.state != "unknown" and self.evidence_ref is None:
            raise ValueError("notification.external_evidence_required")


def record_external_delivery(receipt: ExternalDeliveryReceipt) -> JournalRecord:
    """Adapt an owner-qualified receipt for registration by that owner."""
    return audit_record("notification." + receipt.stage, receipt.scope_id, receipt.dispatch_id,
                        receipt.observed_at_utc, details={
                            "attempt_id": receipt.attempt_id, "consumer_id": receipt.consumer_id,
                            "state": receipt.state, "evidence_ref": receipt.evidence_ref,
                            "reason_code": receipt.reason_code,
                        })


@dataclass(frozen=True, slots=True)
class DownstreamStage:
    stage: str
    attempt_id: str
    state: Literal["confirmed", "failed", "unknown", "conflicting"]


def project_downstream(
    records: Iterable[JournalRecord], *, scope_id: str, dispatch_id: str, consumer_id: str,
    max_records: int = 10_000,
) -> tuple[DownstreamStage, ...]:
    """Reduce owner-qualified observations already admitted by the calling host."""
    for value in (scope_id, dispatch_id, consumer_id):
        safe_token(value)
    if type(max_records) is not int or not 1 <= max_records <= 100_000:
        raise ValueError("notification.scan_limit_invalid")
    by_stage: dict[tuple[str, str], set[str]] = {}
    kinds = {"notification.transport_accepted", "notification.delivered", "notification.read"}
    for number, record in enumerate(records, 1):
        if number > max_records:
            raise ValueError("notification.scan_limit")
        if (record.record_type != "domain_fact" or record.kind not in kinds
                or record.subject is None or record.subject.namespace != "notification"
                or record.subject.object_id != dispatch_id or record.payload.get("scope_id") != scope_id
                or record.payload.get("consumer_id") != consumer_id or type(record.payload.get("data_version")) is not int
                or record.payload["data_version"] != 1):
            continue
        stage, attempt = record.kind.removeprefix("notification."), record.payload.get("attempt_id")
        state, evidence = record.payload.get("state"), record.payload.get("evidence_ref")
        if type(attempt) is not str or state not in ("confirmed", "failed", "unknown"):
            raise ValueError("notification.external_receipt_invalid")
        if state != "unknown":
            safe_token(evidence)
        by_stage.setdefault((stage, safe_token(attempt)), set()).add(state)
    return tuple(DownstreamStage(stage, attempt,
                                  "conflicting" if {"confirmed", "failed"} <= states
                                  else "confirmed" if "confirmed" in states
                                  else "failed" if "failed" in states else "unknown")
                 for (stage, attempt), states in sorted(by_stage.items()))
