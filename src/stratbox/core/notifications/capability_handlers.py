"""Bounded command leaves for explicit preparation and required handoff."""
from __future__ import annotations

from dataclasses import dataclass
from random import uniform

from stratbox.core.execution import Completion, EffectReceipt, OperationFailure
from stratbox.core.notifications.dispatch.contracts import DeliverRequest, ReconcileDeliveryRequest, RetryPolicy
from stratbox.core.notifications.dispatch.delivery import deliver_work
from stratbox.core.notifications.dispatch.reconciliation import reconcile_work
from stratbox.core.notifications.dispatch.qualification import qualify_receipt
from stratbox.core.notifications.dispatch.preparation_contracts import PrepareRequest, PreparationReport
from stratbox.core.observability import JournalReadLimits
from stratbox.core.notifications.contracts import CapabilitySelector
from stratbox.shared.identifiers import safe_token
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
    complete: bool = False
    subscription_revision: int | None = None


def _runtime(invocation):
    runtime = invocation.provider('notification_runtime')
    if not isinstance(runtime, NotificationRuntime):
        raise OperationFailure('notification.runtime_required')
    return runtime


def prepare_intents(request, invocation):
    """Freeze a complete required dispatch set over one prepared journal head.

    Page size bounds each read. Exhausting the preparation or history budget
    fails the obligation before any consumer handoff, preserving checkpointed
    progress for a later explicitly retried invocation.
    """
    runtime = _runtime(invocation)
    key = request['key']
    if not isinstance(key, CheckpointKey):
        raise OperationFailure('notification.checkpoint_key_required')
    page_size = request.get('max_dispatches', 128)
    max_pages = request.get('max_pages', 50)
    max_scan_pages = request.get('max_scan_pages', 1000)
    max_selected = request.get('max_selected_dispatches', 10_000)
    if type(page_size) is not int or not 1 <= page_size <= 1000:
        raise OperationFailure('notification.dispatch_limit_invalid')
    if type(max_pages) is not int or not 1 <= max_pages <= 50:
        raise OperationFailure('notification.preparation_page_limit_invalid')
    if type(max_scan_pages) is not int or not 1 <= max_scan_pages <= 100_000:
        raise OperationFailure('notification.scan_page_limit_invalid')
    if type(max_selected) is not int or not 1 <= max_selected <= 100_000:
        raise OperationFailure('notification.selected_dispatch_limit_invalid')
    if request.get('after_position', 0) != 0:
        raise OperationFailure('notification.required_selection_from_start')
    selector = request.get('selector')
    if selector is not None and not isinstance(selector, CapabilitySelector):
        raise OperationFailure('notification.capability_selector_required')
    exact_ids = request.get('dispatch_ids', ())
    if not isinstance(exact_ids, tuple) or len(exact_ids) > max_selected or len(set(exact_ids)) != len(exact_ids):
        raise OperationFailure('notification.dispatch_set_invalid')
    for dispatch_id in exact_ids:
        safe_token(dispatch_id)
    effect = request.get('effect')
    if effect is not None and (not isinstance(effect, StoredBytesReceipt)
            or effect.status not in {'stored', 'already_present'} or effect.effect_id is None):
        raise OperationFailure('notification.confirmed_storage_receipt_required')
    expected_topic = request.get('expected_topic')
    subscription = runtime.state.get_subscription(key.scope_id, key.subscription_id)
    if subscription is None:
        raise OperationFailure('subscription.not_found')
    if expected_topic is not None and subscription.spec.topic_id != expected_topic:
        raise OperationFailure('notification.required_topic_mismatch')
    historical = request.get('allow_historical', False)
    if type(historical) is not bool:
        raise OperationFailure('notification.history_policy_invalid')
    answer = prepare_work(PrepareRequest(key, limits=JournalReadLimits(max_positions=page_size),
        mode='replay' if key.replay_id is not None else 'catch_up', max_pages=max_pages), runtime, invocation)
    report = answer.value if isinstance(answer, Completion) else answer
    if isinstance(answer, Completion):
        raise OperationFailure(answer.diagnostics[0], outcome='unknown' if answer.outcome == 'unknown' else 'failed')
    if not isinstance(report, PreparationReport) or not report.caught_up:
        raise OperationFailure('notification.required_preparation_incomplete')
    subscription = runtime.state.get_subscription(key.scope_id, key.subscription_id)
    if subscription is None:
        raise OperationFailure('subscription.not_found')
    source_run = request.get('source_run_id')
    if source_run is None and not historical and not exact_ids and effect is None:
        source_run = invocation.context.correlation.run_id
    selected, after = [], 0
    found = set()
    for _ in range(max_scan_pages):
        invocation.check_cancelled()
        rows = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=page_size + 1, after=after)
        has_more = len(rows) > page_size
        page = rows[:page_size]
        for row in page:
            intent = row.intent
            if intent.event.cursor.stream != key.stream:
                continue
            if exact_ids and intent.dispatch_id not in exact_ids:
                continue
            if not exact_ids and row.state not in PENDING_STATES | {'consumer_accepted'}:
                continue
            # Historical reconciliation addresses unresolved obligations; old
            # accepted rows are final evidence and need no journal re-read.
            if historical and not exact_ids and effect is None and source_run is None and row.state == 'consumer_accepted':
                continue
            evidence = intent.selection_evidence
            if evidence is None:
                if exact_ids:
                    raise OperationFailure('notification.selection_evidence_missing')
                continue
            if not evidence.matches(selector):
                continue
            if (not historical or not exact_ids) and not evidence.matches(subscription.spec.selector):
                continue
            if effect is not None:
                if evidence.record_kind != 'effect.confirmed' or evidence.effect_id != effect.effect_id:
                    continue
                if evidence.identity != effect.identity:
                    raise OperationFailure('notification.effect_identity_mismatch')
            if source_run is not None and evidence.run_id != source_run:
                continue
            if (intent.event.cursor.epoch_id == report.head.epoch_id
                    and intent.event.cursor.last_offset > report.target_offset):
                continue
            selected.append(intent.dispatch_id)
            found.add(intent.dispatch_id)
            if len(selected) > max_selected:
                raise OperationFailure('notification.required_selection_limit')
        after += len(page)
        if not has_more:
            break
    else:
        raise OperationFailure('notification.required_selection_incomplete')
    if exact_ids and found != set(exact_ids):
        raise OperationFailure('notification.required_intent_missing')
    return PreparedNotificationBatch(key, tuple(selected), report, complete=True,
                                     subscription_revision=subscription.revision)


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
    if (not prepared.complete or prepared.next_position is not None
            or not isinstance(prepared.report, PreparationReport) or not prepared.report.caught_up):
        raise OperationFailure('notification.required_selection_incomplete')
    subscription = runtime.state.get_subscription(prepared.key.scope_id, prepared.key.subscription_id)
    if subscription is None or subscription.revision != prepared.subscription_revision:
        raise OperationFailure('subscription.revision_conflict')
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
