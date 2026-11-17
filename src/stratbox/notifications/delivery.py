"""Fenced handoff to a bound consumer, with qualified receipt recovery."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import json
from random import uniform
from typing import Callable, Literal
from uuid import uuid4

from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution import Completion, EffectReceipt, Invocation, OperationFailure
from stratbox.execution.contracts import safe_token
from stratbox.observability import JournalReadLimits, RequiredJournalGate

from .audit import audit_record
from .contracts import AdmittedHandoff, HandoffLookup, HandoffReceipt, NotificationIntent
from .preparation import (
    MAX_ENVELOPE_BYTES, _metadata, _projection, dispatch_key, read_page,
)
from .runtime import NotificationRuntime, access, need_access, require_admission, require_binding
from .state import Attempt, Dispatch, DispatchUpdate, PENDING_STATES, StateMutation, StateReceipt, commit_and_lookup
from .subscriptions import _head
from .topics import is_service_event, match_conditions
from stratbox.observability.schema import ValueRule


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 60
    max_delay_seconds: int = 3600
    lifetime_seconds: int = 7 * 24 * 3600
    claim_seconds: int = 120

    def __post_init__(self) -> None:
        values = (self.max_attempts, self.base_delay_seconds, self.max_delay_seconds,
                  self.lifetime_seconds, self.claim_seconds)
        if (any(type(value) is not int or not 1 <= value <= 366 * 24 * 3600 for value in values)
                or self.max_attempts > 64 or self.base_delay_seconds > self.max_delay_seconds):
            raise ValueError("notification.retry_policy_invalid")

    def expires(self, intent: NotificationIntent) -> datetime:
        return intent.prepared_at_utc + timedelta(seconds=self.lifetime_seconds)

    def next_due(
        self, number: int, now: datetime, receipt: HandoffReceipt,
        jitter: Callable[[float, float], float],
    ) -> datetime:
        delay = min(self.max_delay_seconds, self.base_delay_seconds * 2**(number - 1))
        observed = jitter(delay / 2, delay)
        if not delay / 2 <= observed <= delay:
            raise ValueError("notification.retry_jitter_invalid")
        planned = now + timedelta(seconds=observed)
        return max(planned, receipt.retry_after_utc) if receipt.retry_after_utc is not None else planned


@dataclass(frozen=True, slots=True)
class DeliverRequest:
    scope_id: str
    dispatch_id: str
    expected_version: int | None = None

    def __post_init__(self) -> None:
        safe_token(self.scope_id)
        safe_token(self.dispatch_id)
        if self.expected_version is not None and (type(self.expected_version) is not int or self.expected_version < 1):
            raise ValueError("notification.dispatch_version_invalid")


@dataclass(frozen=True, slots=True)
class ReconcileDeliveryRequest:
    scope_id: str
    dispatch_id: str
    attempt_id: str

    def __post_init__(self) -> None:
        for value in (self.scope_id, self.dispatch_id, self.attempt_id):
            safe_token(value)


@dataclass(frozen=True, slots=True)
class QualifyDeliveryRequest:
    lookup: HandoffLookup
    receipt: HandoffReceipt | None


@dataclass(frozen=True, slots=True)
class QualifiedHandoff:
    state: Literal["accepted", "not_accepted", "unknown"]
    reason_code: str
    receipt: HandoffReceipt | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    dispatch_id: str
    state: str
    reason_code: str | None
    next_action: Literal["done", "deliver", "wait", "reconcile", "reload_state"]
    attempt_id: str | None = None
    next_due_at_utc: datetime | None = None
    state_command_id: str | None = None


def qualify_receipt(lookup: HandoffLookup, receipt: HandoffReceipt | None) -> QualifiedHandoff:
    if receipt is None:
        return QualifiedHandoff("unknown", "notification.acknowledgement_unconfirmed")
    if not isinstance(receipt, HandoffReceipt) or (
        receipt.dispatch_id, receipt.attempt_id, receipt.route, receipt.route_revision, receipt.payload_identity
    ) != (lookup.dispatch_id, lookup.attempt_id, lookup.route, lookup.route_revision, lookup.payload_identity):
        return QualifiedHandoff("unknown", "notification.receipt_mismatch")
    if receipt.state == "unknown" or receipt.evidence_ref is None:
        return QualifiedHandoff("unknown", receipt.reason_code or "notification.acknowledgement_unconfirmed")
    if receipt.state == "accepted":
        return QualifiedHandoff("accepted", "notification.consumer_accepted", receipt)
    return QualifiedHandoff("not_accepted", receipt.reason_code or "notification.not_accepted", receipt)


def _summary(row: Dispatch, *, command_id: str | None = None) -> DeliveryResult:
    next_action = {
        "ready": "deliver", "retry_due": "wait", "in_flight": "reconcile", "unknown": "reconcile",
    }.get(row.state, "done")
    return DeliveryResult(row.intent.dispatch_id, row.state, row.reason_code, next_action,
                          row.attempts[-1].lookup.attempt_id if row.attempts else None,
                          row.next_due_at_utc, command_id)


def _contains(current, saved) -> bool:
    if isinstance(saved, dict):
        return isinstance(current, dict) and all(
            key in current and _contains(current[key], value) for key, value in saved.items()
        )
    if isinstance(saved, list):
        return isinstance(current, (tuple, list)) and len(saved) == len(current) and all(
            _contains(a, b) for a, b in zip(current, saved)
        )
    return type(current) is type(saved) and current == saved


def _verify_payload(intent: NotificationIntent, subscription, topic, profile, record, data, version, grant) -> None:
    if (type(intent.envelope_bytes) is not bytes or len(intent.envelope_bytes) > MAX_ENVELOPE_BYTES
            or ByteIdentity.of(intent.envelope_bytes) != intent.payload_identity):
        raise ValueError("notification.payload_conflict")
    envelope = json.loads(intent.envelope_bytes)
    if not isinstance(envelope, dict) or canonical_manifest_bytes(envelope) != intent.envelope_bytes:
        raise ValueError("notification.payload_conflict")
    key = dispatch_key(subscription, intent.event.source_authority_id, topic.topic_id,
                       topic.event_key_kind, topic.event_key(record, data))
    metadata = _metadata(record, version, intent.metadata)
    header = {
        "envelope_version": 1, "dispatch_id": key,
        "topic_id": topic.topic_id, "topic_version": topic.version, "projection_id": profile.projection_id,
        "projection_version": profile.version, "consumer_id": subscription.spec.route.consumer_id,
        "subscription_id": subscription.spec.subscription_id,
        "subscription_revision": intent.subscription_revision, **metadata,
    }
    selected = envelope.pop("data", None)
    if key != intent.dispatch_id or envelope != header:
        raise ValueError("notification.payload_conflict")
    ValueRule("object", fields=profile.fields).validate(selected)
    if not intent.metadata <= profile.metadata & grant.metadata or not _contains(
        _projection(profile, data, grant), selected,
    ):
        raise PermissionError("notification.projection_unavailable")


def _load(request, runtime: NotificationRuntime, invocation: Invocation):
    require_admission(runtime, invocation.context, request.scope_id)
    row = runtime.state.get_dispatch(request.scope_id, request.dispatch_id)
    if row is None or row.intent.scope_id != request.scope_id or row.intent.dispatch_id != request.dispatch_id:
        raise OperationFailure("notification.dispatch_not_found")
    sub = runtime.state.get_subscription(request.scope_id, row.intent.subscription_id)
    if sub is None:
        raise OperationFailure("subscription.not_found")
    visible = access(runtime, "inspect", sub.spec, invocation.context.clock.now(),
                     stream=row.intent.event.cursor.stream, authority_id=row.intent.event.source_authority_id,
                     intent=row.intent)
    if visible.state == "denied":
        raise OperationFailure("notification.dispatch_not_found")
    need_access(visible)
    return row, sub


def _persist(runtime, row, after, sub, code, invocation, **details) -> StateReceipt:
    now = invocation.context.clock.now()
    intent = row.intent
    record = audit_record(code, intent.scope_id, intent.dispatch_id, now, details={
        "subscription_id": intent.subscription_id, "revision": sub.revision, "state": after.state,
        "dispatch_version": after.version, **details,
    }, correlation=invocation.context.correlation, cause=intent.event.record_id)
    mutation = StateMutation(intent.scope_id, intent.subscription_id, sub.revision,
                             dispatch_updates=(DispatchUpdate(row.version, after),), audit=(record,))
    receipt = commit_and_lookup(runtime.state, mutation)
    if receipt.state in {"confirmed", "unknown"}:
        invocation.effect(EffectReceipt(
            "notification.state_commit", receipt.state, effect_id=receipt.command_id,
            guarantee="atomic_state", reconciliation_owner="notification_state",
        ))
    return receipt


def _state_failure(row: Dispatch, receipt: StateReceipt):
    value = replace(_summary(row), reason_code=receipt.reason_code, next_action="reload_state",
                    state_command_id=receipt.command_id)
    state = "unknown" if receipt.state == "unknown" else "failed"
    return Completion(value, state, receipt.reason_code or "notification.state_commit_failed")


def _stop(runtime, row, sub, state: str, reason: str, invocation):
    after = replace(row, version=row.version + 1, state=state, reason_code=reason, next_due_at_utc=None)
    receipt = _persist(runtime, row, after, sub, f"notification.{state}", invocation, reason_code=reason)
    return _summary(after) if receipt.state == "confirmed" else _state_failure(row, receipt)


def _admit(row, sub, runtime: NotificationRuntime, invocation: Invocation):
    intent = row.intent
    spec = sub.spec
    if (intent.route, intent.topic_id, intent.topic_version, intent.projection_id, intent.projection_version) != (
        spec.route, spec.topic_id, spec.topic_version, spec.projection_id, spec.projection_version
    ):
        raise PermissionError("notification.subscription_changed")
    stream = intent.event.cursor.stream
    binding = runtime.source_for(stream)
    require_admission(runtime, invocation.context, intent.scope_id, binding)
    if stream not in spec.streams or binding.source_authority_id != intent.event.source_authority_id:
        raise ValueError("journal.source_binding_mismatch")
    topic, profile = runtime.catalog.resolve(spec)
    if not topic.in_scope(binding.source_authority_id):
        raise PermissionError("notification.source_not_allowed")
    consumer = runtime.consumer_for(spec)
    if binding.profile == "resumable":
        if runtime.state.durable is not True or consumer.kind != "durable_inbox":
            raise OperationFailure("notification.durable_inbox_required")
        guarantees = ("recipient_bound", "durable_acceptance", "idempotent_acceptance")
    else:
        if consumer.kind != "in_process":
            raise OperationFailure("notification.local_consumer_required")
        guarantees = ("recipient_bound",)
    require_binding(invocation.context, intent.scope_id, "notification", consumer.consumer, *guarantees)
    head = _head(binding)
    before = replace(intent.event.cursor, last_offset=intent.event.cursor.last_offset - 1)
    page = read_page(binding, before, head, JournalReadLimits(max_positions=1))
    if not page.entries:
        raise OperationFailure(page.problem.code if page.problem else "journal.record_unavailable")
    entry = page.entries[0]
    record = entry.record
    if record is None or (record.record_id, entry.identity) != (intent.event.record_id, intent.event.record_identity):
        raise ValueError("journal.record_identity_mismatch")
    now = invocation.context.clock.now()
    grant = access(runtime, "accept", spec, now, stream=stream, record=record,
                   authority_id=binding.source_authority_id, intent=intent)
    if grant.state == "denied":
        raise PermissionError("notification.access_denied")
    need_access(grant)
    if grant.route_revision is None:
        raise OperationFailure("notification.route_revision_required")
    schema = runtime.catalog.input_schema(topic, record)
    data = schema.validate(record)
    if (is_service_event(record) or any(condition.field not in grant.fields for condition in spec.filters)
            or (topic.eligible is not None and not topic.eligible(record, data))
            or not topic.permits_mode(data, spec.filters) or not match_conditions(spec.filters, data)):
        raise PermissionError("notification.subscription_changed")
    _verify_payload(intent, sub, topic, profile, record, data, schema.version, grant)
    return consumer, grant, record


def _begin(runtime, row, sub, grant, policy, invocation):
    now = invocation.context.clock.now()
    intent = row.intent
    lookup = HandoffLookup(intent.scope_id, intent.dispatch_id, uuid4().hex, intent.route,
                           grant.route_revision, intent.payload_identity, row.version + 1)
    claim_until = min(now + timedelta(seconds=policy.claim_seconds), policy.expires(intent))
    if grant.expires_at_utc is not None:
        claim_until = min(claim_until, grant.expires_at_utc)
    attempt = Attempt(lookup, len(row.attempts) + 1, runtime.actor_id, now, claim_until, sub.revision)
    claimed = replace(row, version=row.version + 1, state="in_flight",
                      attempts=(*row.attempts, attempt), next_due_at_utc=None, reason_code=None)
    receipt = _persist(runtime, row, claimed, sub, "notification.attempt_started", invocation,
                       attempt_id=lookup.attempt_id, attempt_no=attempt.number,
                       fence=lookup.fence, route_revision=lookup.route_revision, grant_ref=grant.grant_ref)
    return claimed, attempt, receipt


def _after(
    row: Dispatch, sub, qualified: QualifiedHandoff, policy: RetryPolicy, now: datetime, jitter,
) -> Dispatch:
    latest = row.attempts[-1]
    due = None
    if qualified.state == "accepted":
        state = "consumer_accepted"
    elif qualified.state == "unknown":
        state = "unknown"
    elif sub.status != "active" or qualified.reason_code == "notification.access_denied":
        state = "cancelled"
    elif not qualified.receipt.retryable:
        state = "rejected"
    elif latest.number >= policy.max_attempts or now >= policy.expires(row.intent):
        state = "expired"
    else:
        due = policy.next_due(latest.number, now, qualified.receipt, jitter)
        state = "retry_due" if due < policy.expires(row.intent) else "expired"
        if state == "expired":
            due = None
    return replace(row, version=row.version + 1, state=state, next_due_at_utc=due,
                   attempts=(*row.attempts[:-1], replace(latest, receipt=qualified.receipt)),
                   reason_code=qualified.reason_code)


def _finish(runtime, row, attempt, qualified, policy, invocation, *, reconciled=False, jitter=uniform):
    intent = row.intent
    codes = {
        "consumer_accepted": "notification.consumer_accepted", "unknown": "notification.attempt_unknown",
        "retry_due": "notification.retry_scheduled", "rejected": "notification.attempt_rejected",
    }
    for _ in range(3):
        current = runtime.state.get_dispatch(intent.scope_id, intent.dispatch_id)
        sub = runtime.state.get_subscription(intent.scope_id, intent.subscription_id)
        if current is None or sub is None:
            raise OperationFailure("notification.state_unavailable", outcome="unknown")
        if (current.state not in {"in_flight", "unknown"} or not current.attempts
                or current.attempts[-1].lookup != attempt.lookup):
            return _summary(current)
        if current.state == "unknown" and qualified.state == "unknown" and current.reason_code == qualified.reason_code:
            return Completion(_summary(current), "unknown", qualified.reason_code)
        after = _after(current, sub, qualified, policy, invocation.context.clock.now(), jitter)
        code = "notification.reconciled" if reconciled else codes.get(after.state, f"notification.{after.state}")
        receipt = _persist(runtime, current, after, sub, code, invocation,
                           attempt_id=attempt.lookup.attempt_id, reason_code=qualified.reason_code,
                           receipt_ref=qualified.receipt.evidence_ref if qualified.receipt else None)
        if receipt.state == "conflict":
            continue
        if receipt.state != "confirmed":
            return _state_failure(current, receipt)
        result = _summary(after)
        if qualified.state == "unknown":
            return Completion(result, "unknown", qualified.reason_code)
        if qualified.state == "not_accepted":
            return Completion(result, "failed", qualified.reason_code)
        return result
    return Completion(_summary(row), "unknown", "notification.dispatch_conflict")


def deliver_work(
    request: DeliverRequest, runtime: NotificationRuntime, invocation: Invocation, *,
    policy: RetryPolicy, gate: RequiredJournalGate | None, jitter,
):
    invocation.stage("load_dispatch")
    row, sub = _load(request, runtime, invocation)
    if request.expected_version is not None and request.expected_version != row.version:
        raise OperationFailure("notification.dispatch_conflict")
    if row.state not in PENDING_STATES or row.state in {"in_flight", "unknown"}:
        return _summary(row)
    if runtime.paused:
        raise OperationFailure("notification.processing_paused")
    now = invocation.context.clock.now()
    if sub.status != "active":
        return _stop(runtime, row, sub, "cancelled", "subscription.not_active", invocation)
    if row.intent.subscription_revision < sub.activation_revision:
        return _stop(runtime, row, sub, "cancelled", "subscription.activation_changed", invocation)
    if now >= policy.expires(row.intent) or len(row.attempts) >= policy.max_attempts:
        return _stop(runtime, row, sub, "expired", "notification.retry_exhausted", invocation)
    if row.next_due_at_utc is not None and now < row.next_due_at_utc:
        return _summary(row)

    invocation.stage("admit_handoff")
    try:
        consumer, grant, record = _admit(row, sub, runtime, invocation)
    except PermissionError as error:
        return _stop(runtime, row, sub, "cancelled", str(error), invocation)
    except ValueError as error:
        code = str(error)
        if not code.startswith(("journal.", "notification.")):
            code = "notification.payload_conflict"
        return _stop(runtime, row, sub, "quarantined", code, invocation)

    invocation.check_cancelled()
    claimed, attempt, state_receipt = _begin(runtime, row, sub, grant, policy, invocation)
    if state_receipt.state != "confirmed":
        return _state_failure(row, state_receipt)

    intent, lookup = row.intent, attempt.lookup
    reason = None
    retryable = True
    if gate is not None:
        barrier = audit_record("notification.handoff_intent", intent.scope_id, intent.dispatch_id,
                               attempt.started_at_utc, details={"attempt_id": lookup.attempt_id,
                                   "payload_sha256": intent.payload_identity.sha256,
                                   "route_revision": lookup.route_revision},
                               correlation=invocation.context.correlation, cause=intent.event.record_id)
        try:
            gate.require_confirmed(barrier)
        except Exception:
            reason = "notification.audit_unconfirmed"

    now = invocation.context.clock.now()
    current = runtime.state.get_subscription(intent.scope_id, intent.subscription_id)
    current_grant = access(runtime, "accept", sub.spec, now, stream=intent.event.cursor.stream,
                           record=record, authority_id=intent.event.source_authority_id, intent=intent)
    try:
        invocation.stage("handoff")
    except OperationFailure:
        reason = "notification.execution_cancelled"
    if reason is None:
        if current is None or current.revision != sub.revision or now >= attempt.claim_until_utc:
            reason = "notification.admission_changed"
        elif current_grant.state == "denied":
            reason, retryable = "notification.access_denied", False
        elif current_grant.state == "unknown" or current_grant.route_revision != lookup.route_revision:
            reason = "notification.admission_changed"
        elif (current_grant.fields, current_grant.metadata) != (grant.fields, grant.metadata):
            try:
                _, current_grant, _ = _admit(row, sub, runtime, invocation)
                if current_grant.route_revision != lookup.route_revision:
                    reason = "notification.admission_changed"
            except PermissionError:
                reason, retryable = "notification.access_denied", False
            except (OperationFailure, ValueError):
                reason = "notification.admission_changed"
    if reason is not None:
        absent = HandoffReceipt(intent.dispatch_id, lookup.attempt_id, lookup.route, lookup.route_revision,
                                lookup.payload_identity, "not_accepted", now, evidence_ref=lookup.attempt_id,
                                reason_code=reason, retryable=retryable)
        return _finish(runtime, claimed, attempt, qualify_receipt(lookup, absent), policy, invocation, jitter=jitter)

    effect = EffectReceipt("notification.handoff", "unknown", effect_id=intent.dispatch_id,
                           identity=intent.payload_identity, guarantee="consumer_acceptance",
                           reconciliation_owner="consumer")
    invocation.effect(effect)
    received = None
    expires = attempt.claim_until_utc
    if current_grant.expires_at_utc is not None:
        expires = min(expires, current_grant.expires_at_utc)
    try:
        received = consumer.consumer.accept(AdmittedHandoff(
            lookup, intent, current_grant.grant_ref, expires, attempt.subscription_revision,
        ))
    except Exception:
        pass
    qualified = qualify_receipt(lookup, received)
    stage = {"accepted": "confirmed", "not_accepted": "failed", "unknown": "unknown"}[qualified.state]
    invocation.effect(replace(effect, state=stage))
    return _finish(runtime, claimed, attempt, qualified, policy, invocation, jitter=jitter)


def reconcile_work(request: ReconcileDeliveryRequest, runtime: NotificationRuntime, invocation: Invocation, *, policy, jitter):
    invocation.stage("load_attempt")
    row, sub = _load(request, runtime, invocation)
    if not row.attempts or row.attempts[-1].lookup.attempt_id != request.attempt_id:
        raise OperationFailure("notification.attempt_mismatch")
    if row.state not in {"in_flight", "unknown"}:
        return _summary(row)
    now = invocation.context.clock.now()
    if row.state == "in_flight" and now < row.attempts[-1].claim_until_utc:
        return _summary(row)
    need_access(access(runtime, "reconcile", sub.spec, now, intent=row.intent))
    consumer = runtime.consumer_for(sub.spec)
    binding = runtime.source_for(row.intent.event.cursor.stream)
    if binding.profile == "resumable" and (runtime.state.durable is not True or consumer.kind != "durable_inbox"):
        raise OperationFailure("notification.durable_inbox_required")
    guarantees = ("recipient_bound", "durable_acceptance", "idempotent_acceptance") if (
        binding.profile == "resumable"
    ) else ("recipient_bound",)
    if binding.profile == "local_snapshot" and consumer.kind != "in_process":
        raise OperationFailure("notification.local_consumer_required")
    require_binding(invocation.context, request.scope_id, "notification", consumer.consumer, *guarantees)
    invocation.stage("owner_lookup")
    attempt = row.attempts[-1]
    observed = None
    try:
        observed = consumer.consumer.lookup(attempt.lookup)
    except Exception:
        pass
    qualified = qualify_receipt(attempt.lookup, observed)
    return _finish(runtime, row, attempt, qualified, policy, invocation, reconciled=True, jitter=jitter)
