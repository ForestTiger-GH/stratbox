"""Explicit composition and admission for the official notification path."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from stratbox.base.capabilities import CapabilityRequirement, select_provider
from stratbox.execution import ExecutionContext, OperationFailure
from stratbox.execution.contracts import safe_token
from stratbox.observability import (
    JournalHead, JournalRecord, JournalSource, RequiredJournalGate, SourceProfile, StreamKey,
)

from .contracts import (
    AccessDecision, AccessRequest, NotificationAuthority, NotificationConsumer,
    NotificationIntent, NotificationRoute, SubscriptionSpec,
)
from .state import NotificationStateReader, NotificationStateStore
from .topics import TopicCatalog


@dataclass(frozen=True, slots=True)
class SourceBinding:
    stream: StreamKey
    source_authority_id: str
    profile: SourceProfile
    source: JournalSource = field(repr=False)

    def __post_init__(self) -> None:
        safe_token(self.source_authority_id)
        if self.profile not in {"local_snapshot", "resumable"}:
            raise ValueError("journal.source_profile_invalid")

    def head(self, *, epoch_id: str | None = None) -> JournalHead:
        head_for_epoch = getattr(self.source, "head_for_epoch", None) if epoch_id is not None else None
        if epoch_id is not None and callable(head_for_epoch):
            result = head_for_epoch(self.stream, epoch_id)
        else:
            result = self.source.head(self.stream)
        if (not isinstance(result, JournalHead) or result.stream != self.stream
                or result.source_authority_id != self.source_authority_id
                or result.profile != self.profile):
            raise OperationFailure("journal.source_binding_mismatch")
        if epoch_id is not None and result.epoch_id != epoch_id:
            raise OperationFailure("journal.epoch_mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ConsumerBinding:
    scope_id: str
    route: NotificationRoute
    kind: Literal["in_process", "durable_inbox"]
    consumer: NotificationConsumer = field(repr=False)

    def __post_init__(self) -> None:
        safe_token(self.scope_id)
        if self.kind not in {"in_process", "durable_inbox"}:
            raise ValueError("notification.consumer_kind_invalid")


@dataclass(frozen=True, slots=True)
class NotificationReadRuntime:
    actor_id: str
    catalog: TopicCatalog
    authority: NotificationAuthority = field(repr=False)
    state: NotificationStateReader = field(repr=False)
    sources: tuple[SourceBinding, ...]

    def __post_init__(self) -> None:
        safe_token(self.actor_id)
        if (not isinstance(self.sources, tuple) or len(self.sources) > 4096
                or len({binding.stream for binding in self.sources}) != len(self.sources)):
            raise ValueError("journal.source_binding_conflict")

    def source_for(self, stream: StreamKey) -> SourceBinding:
        for binding in self.sources:
            if binding.stream == stream:
                return binding
        raise OperationFailure("journal.source_not_registered")


@dataclass(frozen=True, slots=True)
class NotificationRuntime(NotificationReadRuntime):
    state: NotificationStateStore = field(repr=False)
    consumers: tuple[ConsumerBinding, ...] = ()
    paused: bool = False
    audit_gate: RequiredJournalGate | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        super(NotificationRuntime, self).__post_init__()
        if (not isinstance(self.consumers, tuple) or len(self.consumers) > 4096
                or len({(binding.scope_id, binding.route) for binding in self.consumers}) != len(self.consumers)):
            raise ValueError("notification.consumer_binding_conflict")

    def consumer_for(self, spec: SubscriptionSpec) -> ConsumerBinding:
        for consumer in self.consumers:
            if (consumer.scope_id, consumer.route) == (spec.scope_id, spec.route):
                return consumer
        raise OperationFailure("notification.consumer_not_registered")


def require_binding(
    context: ExecutionContext, scope_id: str, role: str, provider: object, *guarantees: str,
) -> None:
    if context.profile == "managed":
        candidates = tuple(binding for binding in context.bindings if binding.provider is provider)
        select_provider(CapabilityRequirement(role, guarantees=frozenset(guarantees)), candidates,
                        scope_id=scope_id)


def require_admission(
    runtime: NotificationReadRuntime, context: ExecutionContext, scope_id: str,
    binding: SourceBinding | None = None,
) -> None:
    require_binding(context, scope_id, "notification_authority", runtime.authority, "scope_bound")
    require_binding(context, scope_id, "notification_state", runtime.state, "atomic_commit")
    if binding is not None:
        require_binding(context, scope_id, "journal_source", binding.source, "scope_bound", "position_bound")


def access(
    runtime: NotificationReadRuntime, action: str, spec: SubscriptionSpec, now: datetime, *,
    stream: StreamKey | None = None, record: JournalRecord | None = None,
    authority_id: str | None = None, intent: NotificationIntent | None = None,
) -> AccessDecision:
    try:
        decision = runtime.authority.authorize(
            AccessRequest(action, runtime.actor_id, spec, stream, record, authority_id, intent),
        )
    except Exception:
        return AccessDecision("unknown")
    if not isinstance(decision, AccessDecision):
        return AccessDecision("unknown")
    if decision.expires_at_utc is not None and now >= decision.expires_at_utc:
        return AccessDecision("denied")
    return decision


def need_access(decision: AccessDecision) -> None:
    if decision.state == "unknown":
        raise OperationFailure("notification.authority_unavailable", outcome="unknown")
    if decision.state == "denied":
        raise OperationFailure("notification.access_denied")
