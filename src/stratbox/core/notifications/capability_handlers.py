"""Bounded command leaves for explicit preparation and required handoff."""
from __future__ import annotations

from dataclasses import dataclass
from random import uniform

from stratbox.core.execution import Completion, EffectReceipt, OperationFailure
from stratbox.core.notifications.dispatch.contracts import DeliverRequest, ReconcileDeliveryRequest, RetryPolicy
from stratbox.core.notifications.dispatch.delivery import deliver_work, _read_evidence
from stratbox.core.notifications.dispatch.reconciliation import reconcile_work
from stratbox.core.notifications.dispatch.qualification import qualify_receipt
from stratbox.core.notifications.dispatch.preparation_contracts import PrepareRequest
from stratbox.core.notifications.operations import prepare_work
from stratbox.core.notifications.runtime import NotificationRuntime
from stratbox.core.notifications.state.contracts import CheckpointKey, PENDING_STATES
from stratbox.shared.evidence import StoredBytesReceipt


@dataclass(frozen=True, slots=True)
class PreparedNotificationBatch:
    key: CheckpointKey
    dispatch_ids: tuple[str, ...]
    report: object
    next_position: int | None = None


def _runtime(invocation):
    runtime = invocation.provider('notification_runtime')
    if not isinstance(runtime, NotificationRuntime):
        raise OperationFailure('notification.runtime_required')
    return runtime


def prepare_intents(request, invocation):
    runtime = _runtime(invocation)
    key = request['key']
    if not isinstance(key, CheckpointKey):
        raise OperationFailure('notification.checkpoint_key_required')
    limit = request.get('max_dispatches', 128)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise OperationFailure('notification.dispatch_limit_invalid')
    answer = prepare_work(PrepareRequest(key), runtime, invocation)
    report = answer.value if isinstance(answer, Completion) else answer
    after = request.get('after_position', 0)
    if type(after) is not int or after < 0:
        raise OperationFailure('notification.dispatch_position_invalid')
    rows = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=limit + 1, after=after)
    next_position = after + limit if len(rows) > limit else None
    rows = rows[:limit]
    effect = request.get('effect')
    if effect is not None and (not isinstance(effect, StoredBytesReceipt)
            or effect.status not in {'stored', 'already_present'} or effect.effect_id is None):
        raise OperationFailure('notification.confirmed_storage_receipt_required')
    source_run = request.get('source_run_id') or invocation.context.correlation.run_id
    historical = request.get('allow_historical', False)
    if type(historical) is not bool:
        raise OperationFailure('notification.history_policy_invalid')
    selected = []
    for row in rows:
        if row.intent.event.cursor.stream != key.stream or row.state not in PENDING_STATES | {'consumer_accepted'}:
            continue
        record = _read_evidence(runtime.source_for(key.stream), row.intent.event)
        if effect is not None:
            if record.kind != 'effect.confirmed' or record.payload.get('effect_id') != effect.effect_id:
                continue
            expected = dict(sha256=effect.identity.sha256, size=effect.identity.size)
            if record.payload.get('identity') != expected:
                raise OperationFailure('notification.effect_identity_mismatch')
        elif not historical and record.correlation.run_id != source_run:
            continue
        selected.append(row.intent.dispatch_id)
    value = PreparedNotificationBatch(key, tuple(selected), report, next_position)
    if isinstance(answer, Completion):
        return Completion(value, answer.outcome, *answer.diagnostics)
    return value


def _handoff_evidence(runtime, scope_id, dispatch_id, invocation):
    row = runtime.state.get_dispatch(scope_id, dispatch_id)
    if row is None or not row.attempts:
        return
    attempt = row.attempts[-1]
    qualified = qualify_receipt(attempt.lookup, attempt.receipt)
    state = {'accepted': 'confirmed', 'not_accepted': 'failed', 'unknown': 'unknown'}[qualified.state]
    invocation.effect(EffectReceipt('notification.handoff', state, effect_id=dispatch_id,
        identity=row.intent.payload_identity, guarantee='consumer_acceptance', reconciliation_owner='consumer'))


def _dispatch(request, invocation, *, reconciliation=False):
    runtime = _runtime(invocation)
    prepared = request['prepared']
    if not isinstance(prepared, PreparedNotificationBatch):
        raise OperationFailure('notification.prepared_intents_required')
    if not prepared.dispatch_ids:
        raise OperationFailure('notification.required_intent_missing')
    results, outcomes, diagnostics = [], [], []
    for dispatch_id in prepared.dispatch_ids:
        invocation.check_cancelled()
        row = runtime.state.get_dispatch(prepared.key.scope_id, dispatch_id)
        if reconciliation:
            if row is None or not row.attempts:
                raise OperationFailure('notification.attempt_missing')
            answer = reconcile_work(ReconcileDeliveryRequest(prepared.key.scope_id, dispatch_id,
                row.attempts[-1].lookup.attempt_id), runtime, invocation, policy=RetryPolicy(), jitter=uniform)
        else:
            answer = deliver_work(DeliverRequest(prepared.key.scope_id, dispatch_id), runtime, invocation,
                policy=RetryPolicy(), gate=runtime.audit_gate, jitter=uniform)
        value = answer.value if isinstance(answer, Completion) else answer
        results.append(value)
        outcome = answer.outcome if isinstance(answer, Completion) else 'succeeded'
        outcomes.append(outcome)
        if isinstance(answer, Completion):
            diagnostics.extend(answer.diagnostics)
        _handoff_evidence(runtime, prepared.key.scope_id, dispatch_id, invocation)
        if outcome == 'succeeded' and value.state in {'unknown', 'in_flight'}:
            outcomes[-1] = 'unknown'
            diagnostics.append('notification.attempt_unknown')
        elif outcome == 'succeeded' and value.state != 'consumer_accepted':
            outcomes[-1] = 'failed'
            diagnostics.append('notification.required_handoff_unconfirmed')
    if 'unknown' in outcomes:
        return Completion(tuple(results), 'unknown', *(diagnostics or ['notification.attempt_unknown']))
    if any(outcome != 'succeeded' for outcome in outcomes):
        return Completion(tuple(results), 'failed', *(diagnostics or ['notification.required_handoff_unconfirmed']))
    return tuple(results)


def handoff(request, invocation):
    return _dispatch(request, invocation)


def reconcile_handoff(request, invocation):
    return _dispatch(request, invocation, reconciliation=True)
