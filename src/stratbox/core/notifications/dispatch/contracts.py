"""Typed delivery requests, retry budgets and qualified outcomes."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Literal
from stratbox.shared.identifiers import safe_token
from stratbox.core.notifications.contracts import HandoffLookup, HandoffReceipt, NotificationIntent

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
    next_action: Literal["done", "deliver", "wait", "reconcile", "reload_state", "restore_evidence"]
    attempt_id: str | None = None
    next_due_at_utc: datetime | None = None
    state_command_id: str | None = None
