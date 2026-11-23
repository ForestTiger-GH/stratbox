"""Select and project trusted pages before atomically advancing a checkpoint."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution import ExecutionContext, Invocation, OperationFailure
from stratbox.core.observability import (
    JournalCursor, JournalDecodeError, JournalEntry, JournalHead, JournalPage,
    JournalReadLimits, JournalRecord,
)
from stratbox.core.observability.records.contracts import require_utc
from stratbox.core.observability.records.schema import ValueRule

from stratbox.core.notifications.state.audit import audit_record
from stratbox.core.notifications.contracts import AccessDecision, EventPointer, NotificationIntent, Subscription
from stratbox.core.notifications.runtime import NotificationReadRuntime, SourceBinding, access, need_access, require_admission
from stratbox.core.notifications.state.transactions import commit_and_lookup
from stratbox.core.notifications.state.contracts import (
    CheckpointKey, CheckpointUpdate, Dispatch, DispatchUpdate, RecordIdentity, StateMutation,
    StateReceipt,
)
from stratbox.core.notifications.subscriptions import _head
from stratbox.core.notifications.topics import NotificationTopic, Projection, is_service_event, match_conditions

MAX_PREPARED_BYTES = 4 * 1024**2


from stratbox.core.notifications.dispatch.intents import _intent, _metadata, _projection, dispatch_key

from .preparation_contracts import PrepareRequest, InspectRequest, PreparationReport, Inspection
from .evidence import PageEvidence, depend, scope_dependencies, topic_value

def read_page(source: SourceBinding, after: JournalCursor, head: JournalHead, limits: JournalReadLimits) -> JournalPage:
    try:
        page = source.source.read_page(after, head=head, limits=limits)
        page.verify(after, head, limits)
    except JournalDecodeError as error:
        raise OperationFailure(error.code) from None
    except Exception:
        raise OperationFailure("journal.source_unavailable", outcome="unknown") from None
    return page


@dataclass(frozen=True, slots=True)
class _Decision:
    offset: int
    code: str
    record: RecordIdentity | None = None
    intent: NotificationIntent | None = None


def _disposition(
    runtime: NotificationReadRuntime, sub: Subscription, topic: NotificationTopic,
    profile: Projection, entry: JournalEntry, head: JournalHead, at: datetime,
    action: str, known: dict[str, ByteIdentity], batch: dict[str, ByteIdentity],
    evidence: PageEvidence | None = None,
) -> _Decision:
    record = entry.record
    if record is None:
        return _Decision(entry.offset, f"journal.{entry.disposition}")
    proof = RecordIdentity(head.source_authority_id, record.record_id, entry.identity)
    existing = known.get(record.record_id)
    if existing is None:
        existing = runtime.state.get_record_identity(head.stream.scope_id, head.source_authority_id, record.record_id)
        if evidence is not None:
            evidence.add("record_identity", {"record_id": record.record_id, "known_identity": existing})
    if existing is not None and existing != entry.identity:
        raise ValueError("journal.record_identity_conflict")
    known[record.record_id] = entry.identity
    if is_service_event(record) or not any(key[:2] == (record.record_type, record.kind) for key in topic.schemas):
        return _Decision(entry.offset, "notification.not_matched", proof)
    grant = access(runtime, action, sub.spec, at, stream=head.stream, record=record,
                   authority_id=head.source_authority_id)
    if evidence is not None:
        evidence.add("authority_decision", {"offset": entry.offset, "grant": grant})
    if grant.state == "unknown":
        raise ValueError("notification.authority_unavailable")
    if grant.state == "denied" or any(condition.field not in grant.fields for condition in sub.spec.filters):
        return _Decision(entry.offset, "notification.access_denied", proof)
    schema = runtime.catalog.input_schema(topic, record)
    if evidence is not None:
        evidence.add("input_schema", schema)
    data = schema.validate(record)
    if ((topic.eligible is not None and not topic.eligible(record, data))
            or not topic.permits_mode(data, sub.spec.filters) or not match_conditions(sub.spec.filters, data)):
        return _Decision(entry.offset, "notification.not_matched", proof)

    event_key = topic.event_key(record, data)
    dispatch_id = dispatch_key(sub, head.source_authority_id, topic.topic_id, topic.event_key_kind, event_key)
    semantic = entry.identity if topic.event_key_kind == "record" else ByteIdentity.of(canonical_manifest_bytes({
        "subject": (record.subject.namespace, record.subject.object_id) if record.subject else None,
        "payload": {name: data[name] for name in topic.semantic_fields if name in data},
    }))
    previous = runtime.state.get_dispatch(sub.spec.scope_id, dispatch_id)
    if evidence is not None:
        evidence.add("dispatch_state", {"dispatch_id": dispatch_id,
            "semantic_identity": previous.intent.semantic_identity if previous is not None else None})
    previous_identity = previous.intent.semantic_identity if previous is not None else batch.get(dispatch_id)
    if previous_identity is not None:
        if previous_identity != semantic:
            raise ValueError("notification.fact_identity_conflict")
        return _Decision(entry.offset, "notification.duplicate", proof)
    try:
        intent = _intent(sub, topic, profile, head, entry, data=data, data_version=schema.version,
                         grant=grant, now=at, dispatch_id=dispatch_id, event_key=event_key, semantic=semantic)
    except PermissionError:
        return _Decision(entry.offset, "notification.projection_unavailable", proof)
    batch[dispatch_id] = semantic
    return _Decision(entry.offset, "notification.prepared", proof, intent)


@dataclass(frozen=True, slots=True)
class _Scope:
    subscription: Subscription
    source: SourceBinding
    head: JournalHead
    cursor: JournalCursor
    target: int


def _load_scope(
    request: PrepareRequest | InspectRequest, runtime: NotificationReadRuntime,
    context: ExecutionContext, *, preview: bool, invocation: Invocation | None = None,
) -> _Scope:
    key = request.key
    source = runtime.source_for(key.stream)
    require_admission(context=context, runtime=runtime, scope_id=key.scope_id, binding=source)
    sub = runtime.state.get_subscription(key.scope_id, key.subscription_id)
    if sub is None or key.stream not in sub.spec.streams:
        raise OperationFailure("subscription.not_found")
    action = "inspect" if preview else "prepare"
    grant = access(runtime, action, sub.spec, context.clock.now(), stream=key.stream,
                   authority_id=source.source_authority_id)
    depend(invocation, "notification.scope_grant", grant, source=source.source_authority_id)
    need_access(grant)
    if not preview and sub.status != "active":
        raise OperationFailure("subscription.not_active")
    if not preview and source.profile == "resumable" and runtime.state.durable is not True:
        raise OperationFailure("notification.durable_state_required")
    cursor = runtime.state.get_checkpoint(key)
    if key.replay_id is not None:
        replay = runtime.state.get_replay(key)
        if replay is None or context.clock.now() >= replay.expires_at_utc:
            raise OperationFailure("notification.replay_unavailable")
        need_access(access(runtime, "replay", sub.spec, context.clock.now(), stream=key.stream,
                           authority_id=source.source_authority_id))
        head, target = replay.head, replay.last_offset
    else:
        head = _head(source)
        target = head.tail_offset
    if preview:
        cursor = request.after or cursor or head.cursor(head.first_retained - 1)
    if cursor is None:
        raise OperationFailure("notification.checkpoint_missing")
    try:
        head.check(cursor)
    except JournalDecodeError as error:
        raise OperationFailure(error.code) from None
    if cursor.last_offset > target:
        raise OperationFailure("journal.cursor_ahead")
    scope = _Scope(sub, source, head, cursor, target)
    scope_dependencies(invocation, scope)
    return scope


def _plan(
    scope: _Scope, runtime: NotificationReadRuntime, limits: JournalReadLimits, context: ExecutionContext, *,
    preview: bool, invocation: Invocation | None = None,
) -> tuple[JournalPage, list[_Decision], str | None]:
    topic, profile = runtime.catalog.resolve(scope.subscription.spec)
    if invocation is not None:
        depend(invocation, "notification.topic_projection", topic_value(topic, profile),
            source=scope.source.source_authority_id)
    if not topic.in_scope(scope.source.source_authority_id):
        raise OperationFailure("notification.source_not_allowed")
    remaining = scope.target - scope.cursor.last_offset
    if remaining == 0:
        return JournalPage(scope.head, scope.cursor, ()), [], None
    limits = replace(limits, max_positions=min(limits.max_positions, remaining))
    page = read_page(scope.source, scope.cursor, scope.head, limits)
    planned = []
    known: dict[str, ByteIdentity] = {}
    batch: dict[str, ByteIdentity] = {}
    prepared_bytes = 0
    with PageEvidence(invocation, scope.source.source_authority_id) as evidence:
        evidence.add("page", {"head": page.head, "after": page.after,
            "problem": page.problem, "storage_coverage": page.storage_coverage,
            "capture_coverage": page.capture_coverage, "domain_coverage": page.domain_coverage})
        for entry in page.entries:
            evidence.add("entry", {"offset": entry.offset, "identity": entry.identity,
                "evidence_ref": entry.evidence_ref, "disposition": entry.disposition})
            if invocation is not None:
                invocation.check_cancelled()
            try:
                item = _disposition(runtime, scope.subscription, topic, profile, entry, page.head,
                    context.clock.now(), "inspect" if preview else "prepare", known, batch, evidence)
                if item.intent is not None:
                    prepared_bytes += item.intent.payload_identity.size
                    if prepared_bytes > MAX_PREPARED_BYTES:
                        return page, planned, None
                planned.append(item)
            except ValueError as error:
                code = str(error)
                if not code.startswith(("journal.", "notification.")):
                    code = "notification.projection_invalid"
                return page, planned, code
        return page, planned, page.problem.code if page.problem is not None else None


def _report(
    scope: _Scope, page: JournalPage, decisions: list[_Decision], code: str | None,
) -> PreparationReport:
    reasons = Counter(item.code for item in decisions)
    offset = decisions[-1].offset if decisions else scope.cursor.last_offset
    prepared, duplicates = reasons["notification.prepared"], reasons["notification.duplicate"]
    return PreparationReport(
        scope.head.cursor(offset), scope.head, scope.target, len(decisions), prepared + duplicates,
        prepared, duplicates, len(decisions) - prepared - duplicates, tuple(sorted(reasons.items())),
        page.storage_coverage, page.capture_coverage, page.domain_coverage,
        offset + 1 if code is not None else None, code,
    )


def inspect(
    request: InspectRequest, *, reader: NotificationReadRuntime, context: ExecutionContext | None = None,
) -> Inspection:
    context = context or ExecutionContext()
    scope = _load_scope(request, reader, context, preview=True)
    page, decisions, issue = _plan(scope, reader, request.limits, context, preview=True)
    return Inspection(scope.subscription.revision, _report(scope, page, decisions, issue),
                      tuple(item.intent.envelope_bytes for item in decisions if item.intent is not None))


def _mutation(
    key: CheckpointKey, scope: _Scope, report: PreparationReport, decisions: list[_Decision],
    context: ExecutionContext,
) -> StateMutation:
    now = context.clock.now()
    rows = tuple(DispatchUpdate(None, Dispatch(item.intent)) for item in decisions if item.intent is not None)
    prepared = [
        audit_record("notification.prepared", key.scope_id, intent.dispatch_id, now, details={
            "subscription_id": key.subscription_id, "revision": scope.subscription.revision,
            "topic_id": intent.topic_id, "payload_sha256": intent.payload_identity.sha256,
            "source_record_id": intent.event.record_id, "grant_ref": intent.grant_ref,
        }, correlation=context.correlation, cause=intent.event.record_id)
        for intent in (item.intent for item in decisions) if intent is not None
    ]
    progress = audit_record("notification.page_processed", key.scope_id, key.subscription_id, now, details={
        "head_ref": scope.head.head_ref, "stream_id": key.stream.stream_id,
        "partition_id": key.stream.partition_id, "epoch_id": scope.head.epoch_id,
        "first_offset": scope.cursor.last_offset + 1, "last_offset": report.checkpoint.last_offset,
        "revision": scope.subscription.revision, "replay_id": key.replay_id,
        "reasons": dict(report.reasons), "reason_code": report.reason_code,
        "blocked_at": report.blocked_at, "storage_coverage": report.storage_coverage,
        "capture_coverage": report.capture_coverage, "domain_coverage": report.domain_coverage,
    }, correlation=context.correlation)
    extra = ()
    if key.replay_id is not None and report.caught_up:
        extra = (audit_record("notification.replay_finished", key.scope_id, key.subscription_id, now,
                              details={"replay_id": key.replay_id, "head_ref": scope.head.head_ref,
                                       "last_offset": report.checkpoint.last_offset},
                              correlation=context.correlation),)
    return StateMutation(
        key.scope_id, key.subscription_id, scope.subscription.revision,
        checkpoint_updates=(CheckpointUpdate(key, scope.cursor, report.checkpoint),),
        dispatch_updates=rows, record_identities=tuple(dict.fromkeys(
            item.record for item in decisions if item.record is not None)),
        audit=(progress, *prepared, *extra),
    )


def prepare_page(
    request: PrepareRequest, runtime, invocation: Invocation, scope: _Scope,
) -> tuple[PreparationReport, StateReceipt | None]:
    page, planned, issue = _plan(scope, runtime, request.limits, invocation.context,
                                 preview=False, invocation=invocation)
    while planned or issue is not None:
        report = _report(scope, page, planned, issue)
        receipt = commit_and_lookup(runtime.state, _mutation(request.key, scope, report, planned, invocation.context))
        if receipt.state != "conflict":
            depend(invocation, "notification.commit_admission", {
                "state": receipt.state, "reason_code": receipt.reason_code,
                "checkpoint": report.checkpoint, "examined": report.examined, "prepared": report.prepared,
            })
        if receipt.state != "rejected" or receipt.reason_code != "notification.queue_capacity" or len(planned) <= 1:
            return report, receipt
        planned = planned[:max(1, len(planned) // 2)]
        issue = None
    return _report(scope, page, planned, issue), None
