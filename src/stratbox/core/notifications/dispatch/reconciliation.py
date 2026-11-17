"""Explicit reconciliation of an uncertain consumer handoff."""
from __future__ import annotations
from stratbox.core.execution import Invocation, OperationFailure
from stratbox.core.notifications.contracts import HandoffReceipt
from stratbox.core.notifications.dispatch.contracts import ReconcileDeliveryRequest
from stratbox.core.notifications.dispatch.qualification import qualify_receipt
from stratbox.core.notifications.dispatch.delivery import _load, _summary, _finish
from stratbox.core.notifications.runtime import NotificationRuntime, require_binding, access, need_access
from stratbox.core.notifications.state.contracts import Dispatch

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
