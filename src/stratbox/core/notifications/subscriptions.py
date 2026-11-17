"""Subscription revisions, activation cuts and explicitly authorized replay."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from stratbox.system.execution import Diagnostic, ExecutionContext, OperationFailure
from stratbox.system.execution.contracts import safe_token
from stratbox.system.observability import JournalCursor, JournalDecodeError, JournalHead
from stratbox.system.observability.contracts import require_utc

from .audit import audit_record
from .contracts import Subscription, SubscriptionSpec
from .runtime import NotificationRuntime, SourceBinding, access, need_access, require_admission
from .state import CheckpointKey, CheckpointUpdate, Replay, StateMutation, commit_and_lookup

_ACTIONS = {
    "create": ("disabled", "subscription.created"),
    "enable": ("active", "subscription.activated"),
    "disable": ("disabled", "subscription.disabled"),
    "retire": ("retired", "subscription.retired"),
    "update": (None, "subscription.updated"),
}


@dataclass(frozen=True, slots=True)
class SubscriptionChange:
    action: Literal["create", "update", "enable", "disable", "retire"]
    spec: SubscriptionSpec
    expected_revision: int | None = None


def _commit(runtime: NotificationRuntime, change: StateMutation) -> None:
    receipt = commit_and_lookup(runtime.state, change)
    if receipt.state != "confirmed":
        code = receipt.reason_code or "notification.state_commit_failed"
        diagnostic = Diagnostic(code, evidence_ref=receipt.command_id)
        raise OperationFailure(diagnostic, outcome="unknown" if receipt.state == "unknown" else "failed")


def _current(runtime: NotificationRuntime, key: CheckpointKey) -> Subscription:
    subscription = runtime.state.get_subscription(key.scope_id, key.subscription_id)
    if subscription is None or key.stream not in subscription.spec.streams:
        raise OperationFailure("subscription.not_found")
    return subscription


def _head(binding: SourceBinding, *, epoch_id: str | None = None) -> JournalHead:
    try:
        return binding.head(epoch_id=epoch_id)
    except OperationFailure:
        raise
    except JournalDecodeError as error:
        raise OperationFailure(error.code) from None
    except Exception:
        raise OperationFailure("journal.source_unavailable", outcome="unknown") from None


def _scope_identity(spec: SubscriptionSpec) -> tuple:
    return spec.scope_id, spec.subscription_id, spec.owner_id, spec.streams, spec.route, spec.topic_id


def configure_subscription(
    change: SubscriptionChange, *, runtime: NotificationRuntime, context: ExecutionContext | None = None,
) -> Subscription:
    context = context or ExecutionContext()
    spec = change.spec
    require_admission(runtime, context, spec.scope_id)
    now = require_utc(context.clock.now())
    decision = access(runtime, "configure", spec, now)
    need_access(decision)
    try:
        status, code = _ACTIONS[change.action]
        topic, profile = runtime.catalog.resolve(spec)
    except (KeyError, ValueError) as error:
        raise OperationFailure("subscription.action_invalid" if isinstance(error, KeyError) else str(error)) from None
    if {condition.field for condition in spec.filters} - decision.fields:
        raise OperationFailure("subscription.filter_access_denied")
    current = runtime.state.get_subscription(spec.scope_id, spec.subscription_id)
    if (current.revision if current else None) != change.expected_revision:
        raise OperationFailure("subscription.revision_conflict")
    if current is None:
        if change.action != "create":
            raise OperationFailure("subscription.not_found")
    elif (change.action == "create" or current.status == "retired"
          or (change.action == "enable" and current.status != "disabled")
          or (change.action == "disable" and current.status != "active")):
        raise OperationFailure("subscription.transition_invalid")
    elif _scope_identity(current.spec) != _scope_identity(spec) or (
        change.action != "update" and current.spec != spec
    ):
        raise OperationFailure("subscription.identity_conflict")
    bindings = tuple(runtime.source_for(stream) for stream in spec.streams)
    if any(not topic.in_scope(binding.source_authority_id) for binding in bindings):
        raise OperationFailure("notification.source_not_allowed")
    activation = current.activation if current else ()
    updates: list[CheckpointUpdate] = []
    cuts: list[dict] = []
    if change.action == "enable":
        heads = []
        for binding in bindings:
            require_admission(runtime, context, spec.scope_id, binding)
            need_access(access(runtime, "configure", spec, now, stream=binding.stream,
                               authority_id=binding.source_authority_id))
            head = _head(binding)
            key = CheckpointKey(spec.scope_id, spec.subscription_id, binding.stream)
            previous = runtime.state.get_checkpoint(key)
            if previous is not None and previous.epoch_id == head.epoch_id and previous.last_offset > head.tail_offset:
                raise OperationFailure("journal.cursor_ahead")
            updates.append(CheckpointUpdate(key, previous, head.cursor(head.tail_offset)))
            cuts.append({
                "stream_id": head.stream.stream_id, "partition_id": head.stream.partition_id,
                "head_ref": head.head_ref, "epoch_id": head.epoch_id, "tail_offset": head.tail_offset,
                "previous_epoch": previous.epoch_id if previous else None,
                "previous_offset": previous.last_offset if previous else None,
            })
            heads.append(head)
        activation = tuple(heads)
    revision = (change.expected_revision or 0) + 1
    activated_at = revision if change.action == "enable" else current.activation_revision if current else None
    subscription = Subscription(
        spec, revision, status or current.status, now, decision.grant_ref, activation, activated_at,
    )
    record = audit_record(code, spec.scope_id, spec.subscription_id, now, details={
        "revision": revision, "actor_id": runtime.actor_id, "grant_ref": decision.grant_ref,
        "topic_id": topic.topic_id, "topic_version": topic.version,
        "projection_id": profile.projection_id, "projection_version": profile.version,
        "state": subscription.status, "cuts": cuts,
    }, correlation=context.correlation)
    _commit(runtime, StateMutation(spec.scope_id, spec.subscription_id, change.expected_revision,
                                  subscription, tuple(updates), audit=(record,)))
    return subscription


def register_replay(
    key: CheckpointKey, first_offset: int, last_offset: int, expires_at_utc: datetime, *,
    runtime: NotificationRuntime, context: ExecutionContext | None = None,
) -> Replay:
    context = context or ExecutionContext()
    binding = runtime.source_for(key.stream)
    require_admission(runtime, context, key.scope_id, binding)
    subscription = _current(runtime, key)
    if subscription.status != "active":
        raise OperationFailure("subscription.not_active")
    now = require_utc(context.clock.now())
    grant = access(runtime, "replay", subscription.spec, now, stream=key.stream,
                   authority_id=binding.source_authority_id)
    need_access(grant)
    try:
        if require_utc(expires_at_utc) <= now:
            raise ValueError
        head = _head(binding)
        replay = Replay(key, head, first_offset, last_offset, expires_at_utc, grant.grant_ref)
    except ValueError:
        raise OperationFailure("notification.replay_range_invalid") from None
    record = audit_record("notification.replay_started", key.scope_id, key.subscription_id, now, details={
        "replay_id": key.replay_id, "first_offset": first_offset, "last_offset": last_offset,
        "head_ref": head.head_ref, "revision": subscription.revision, "grant_ref": grant.grant_ref,
    }, correlation=context.correlation)
    update = CheckpointUpdate(key, None, head.cursor(first_offset - 1))
    _commit(runtime, StateMutation(key.scope_id, key.subscription_id, subscription.revision,
                                  checkpoint_updates=(update,), audit=(record,), replay=replay))
    return replay


def amend_checkpoint(
    key: CheckpointKey, *, expected: JournalCursor, head_ref: str, last_offset: int,
    reason_code: str, evidence_ref: str, action: Literal["waive", "rebase"],
    runtime: NotificationRuntime, context: ExecutionContext | None = None,
) -> JournalCursor:
    """Advance past a recorded problem or adopt an explicitly approved new cut."""
    context = context or ExecutionContext()
    for value in (head_ref, reason_code, evidence_ref):
        safe_token(value)
    if action not in {"waive", "rebase"} or (action == "rebase" and key.replay_id is not None):
        raise OperationFailure("notification.checkpoint_action_invalid")
    binding = runtime.source_for(key.stream)
    require_admission(runtime, context, key.scope_id, binding)
    subscription = _current(runtime, key)
    if subscription.status != "active":
        raise OperationFailure("subscription.not_active")
    now = require_utc(context.clock.now())
    grant = access(runtime, action, subscription.spec, now, stream=key.stream,
                   authority_id=binding.source_authority_id)
    need_access(grant)
    head = _head(binding)
    if key.replay_id is not None:
        replay = runtime.state.get_replay(key)
        if replay is None or now >= replay.expires_at_utc or last_offset > replay.last_offset:
            raise OperationFailure("notification.replay_range_invalid")
        head = replay.head
    if head.head_ref != head_ref or expected.stream != key.stream:
        raise OperationFailure("journal.page_snapshot_mismatch")
    try:
        new_cursor = head.cursor(last_offset)
        head.check(new_cursor)
        if expected.epoch_id == head.epoch_id and last_offset <= expected.last_offset:
            raise ValueError
        if action == "waive" and expected.epoch_id != head.epoch_id:
            raise ValueError
    except ValueError:
        raise OperationFailure("notification.checkpoint_range_invalid") from None
    code = "notification.position_waived" if action == "waive" else "notification.position_rebased"
    record = audit_record(code, key.scope_id, key.subscription_id, now, details={
        "actor_id": runtime.actor_id, "grant_ref": grant.grant_ref, "revision": subscription.revision,
        "stream_id": key.stream.stream_id, "partition_id": key.stream.partition_id,
        "previous_epoch": expected.epoch_id, "previous_offset": expected.last_offset,
        "epoch_id": head.epoch_id, "last_offset": new_cursor.last_offset, "head_ref": head.head_ref,
        "reason_code": reason_code, "evidence_ref": evidence_ref, "replay_id": key.replay_id,
    }, correlation=context.correlation)
    _commit(runtime, StateMutation(key.scope_id, key.subscription_id, subscription.revision,
                                  checkpoint_updates=(CheckpointUpdate(key, expected, new_cursor),),
                                  audit=(record,)))
    return new_cursor
