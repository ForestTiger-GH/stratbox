"""Journal-driven notification intent, delivery and acknowledgement actions."""
from collections.abc import Mapping
from dataclasses import replace

from stratbox.shared.data.values import Assessment, fingerprint, immutable
from stratbox.core.execution.service import ExecutionFailure
from ._settings import _option
from ._storage import _provider_scope


def _channel_scope(context,provider,route):
    from stratbox.core.runtime.capabilities import ProviderBinding
    binding=context.service.providers.get('notification')
    scope=getattr(binding,'scope_id',None) if isinstance(binding,ProviderBinding) else None
    identity=binding.provider_id if isinstance(binding,ProviderBinding) else getattr(provider,'provider_id',None)
    if scope is None:
        declared=getattr(provider,'storage_scope',None)
        scope=declared(str(route)) if callable(declared) else getattr(provider,'scope_id',None)
    if not isinstance(scope,str) or not scope or len(scope)>4096:
        raise ExecutionFailure('notification.channel_scope_required')
    return fingerprint((identity,scope,route))


def notification_prepare(inputs, settings, context):
    if 'facts' in inputs and 'page' in inputs:
        raise ExecutionFailure('notification.one_consumption_input_required')
    source = inputs.get('page', inputs.get('facts', ()))
    state = context.provider("notification_state")
    selector, route = _option(context, settings, "selector", {}), _option(context, settings, "route")
    subscription = _option(context, settings, "subscription_id", "default")
    from stratbox.core.notifications.consumption import normalize
    from stratbox.shared.data.journal import JournalPage
    consumption = normalize(source, selector)
    source = replace(source,facts=consumption.facts) if isinstance(source,JournalPage) else consumption.facts
    effect_id = fingerprint(("notification.state", _provider_scope(state, subscription), subscription, selector, route,
        consumption,state.preparation_basis(subscription)))
    def prepare_state():
        # This transaction is idempotent: the cursor and deterministic intent
        # keys are committed together. Replay can safely resolve a lost reply.
        prepared = state.prepare(source, subscription_id=subscription, selector=selector, route=route)
        return {"status": "confirmed", "effect_id": effect_id, "prepared": len(prepared),
            'checkpoint':state.checkpoint(subscription)}
    receipt = context.effect("notification.state", effect_id,
        prepare_state, reconcile=lambda previous: prepare_state(), resource=subscription)
    if receipt.status != "confirmed":
        raise ExecutionFailure('notification.state_unknown' if receipt.status=='unknown' else 'notification.state_rejected',
            outcome='unknown' if receipt.status=='unknown' else 'failed')
    # A repeated preparation confirms the input transaction, then reads the
    # current pending page; its old effect receipt is not a current queue view.
    return {"intents": state.pending(subscription, after_sequence=_option(context, settings, "after_sequence", 0),
        limit=_option(context, settings, "limit", 1000))}


def notification_deliver(inputs, settings, context):
    provider, intent = context.provider("notification"), inputs["intent"]
    if not isinstance(intent,Mapping) or not isinstance(intent.get('id'),str) or not intent['id']:
        raise ExecutionFailure('notification.intent_identity_required')
    sealed=immutable(dict(intent))
    channel_scope=_channel_scope(context,provider,intent.get('route'))
    previous=context.service.lookup_effect(intent['id'])
    if previous is not None and previous.resource!=channel_scope:
        raise ExecutionFailure('notification.channel_scope_conflict')
    if previous is not None and (previous.kind!='notification.deliver'
            or previous.intent is None or fingerprint(previous.intent)!=fingerprint(sealed)):
        raise ExecutionFailure('notification.intent_content_conflict')
    subscription = intent.get("subscription_id")
    state = context.provider('notification_state') if subscription is not None else None
    if subscription is not None and (not callable(getattr(state, "acknowledge", None))
            or not callable(getattr(state,'intent',None))):
        raise ExecutionFailure("notification.acknowledgement_state_required")
    if subscription is not None:
        authoritative=state.intent(subscription,intent['id'])
        if authoritative is None:
            if previous is None or previous.status!='confirmed':
                raise ExecutionFailure('notification.pending_intent_missing')
        elif fingerprint(authoritative)!=fingerprint(sealed):
            raise ExecutionFailure('notification.intent_content_conflict')
    # Direct acknowledgement, retry lookup and explicit reconciliation enter
    # the same typed admission boundary in the effect coordinator.
    receipt = context.effect("notification.deliver", intent["id"], lambda: provider.deliver(sealed),
        reconcile=lambda previous: provider.lookup(previous.effect_id) if hasattr(provider, "lookup") else None,
        resource=channel_scope,intent=sealed)
    if receipt.status != "confirmed":
        raise ExecutionFailure("notification.delivery_" + receipt.status,
            outcome="unknown" if receipt.status == "unknown" else "failed")
    if subscription is not None:
        acknowledgement_id = fingerprint(("notification.acknowledge", _provider_scope(state, subscription),
            subscription, intent["id"]))
        def acknowledge():
            result = state.acknowledge(subscription, intent["id"], receipt)
            return {"status": "confirmed", "effect_id": acknowledgement_id, 'acknowledgement': result}
        acknowledged = context.effect("notification.state", acknowledgement_id, acknowledge,
            reconcile=lambda previous: acknowledge(), resource=subscription)
        if acknowledged.status != "confirmed":
            raise ExecutionFailure("notification.state_unknown", outcome="unknown")
    return {"receipt": receipt}


def notification_reconcile(inputs, settings, context):
    provider, supplied = context.provider("notification"), inputs["receipt"]
    effect_id=getattr(supplied,'effect_id',None)
    if not isinstance(effect_id,str) or not effect_id:
        raise ExecutionFailure('notification.effect_identity_required')
    receipt=context.service.lookup_effect(effect_id)
    if receipt is None or receipt.kind!='notification.deliver' or not isinstance(receipt.intent,Mapping):
        raise ExecutionFailure('notification.delivery_evidence_required')
    if receipt.intent.get('id')!=effect_id:
        raise ExecutionFailure('notification.intent_content_conflict')
    if receipt.resource!=_channel_scope(context,provider,receipt.intent.get('route')):
        raise ExecutionFailure('notification.channel_scope_conflict')
    return {'assessment':context.service.reconcile_effect(effect_id,provider.lookup,context=context)
        if callable(getattr(provider,'lookup',None)) else Assessment('indeterminate')}
