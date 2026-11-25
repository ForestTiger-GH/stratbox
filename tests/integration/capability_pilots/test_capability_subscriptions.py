"""Subscriptions select journaled results and completion at every public kind."""
from dataclasses import replace
import json

import pytest

from stratbox.capabilities.catalog import CatalogContribution
from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.capabilities.model import (
    Call, CascadeDefinition, CommandDefinition, GraphBody, OperationDefinition,
    OutputRef, PortContract, ScenarioDefinition,
)
from stratbox.core.execution import ExecutionContext
from stratbox.core.notifications import (
    AccessDecision, CapabilitySelector, CheckpointKey, ConsumerBinding, MemoryNotificationState,
    NotificationRoute, NotificationRuntime, SourceBinding, SubscriptionChange, SubscriptionSpec,
    build_catalog, configure_subscription,
)
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract
from .test_required_notification import Inbox


NUMBER = PortContract(DataContract('subscription.number'), int)


def constant(request, invocation):
    return 11


class Authority:
    def authorize(self, request):
        fields = frozenset(field.name for topic in build_catalog().definitions()
            for projection in topic.projections for field in projection.fields)
        return AccessDecision('allow', fields, frozenset({'event_ref', 'occurred_at_utc'}), 'grant', 'route.1')


def definitions():
    command = CommandDefinition('subscription.command', __name__ + ':constant', outputs={'value': NUMBER})
    operation = OperationDefinition('subscription.operation', GraphBody((
        Call('command', command.capability_id),), {'value': OutputRef('command')}), outputs={'value': NUMBER})
    scenario = ScenarioDefinition('subscription.scenario', GraphBody((
        Call('operation', operation.capability_id),), {'value': OutputRef('operation')}), outputs={'value': NUMBER})
    cascade = CascadeDefinition('subscription.cascade', GraphBody((
        Call('scenario', scenario.capability_id),), {'value': OutputRef('scenario')}), outputs={'value': NUMBER})
    return command, operation, scenario, cascade


def runtime_for(box, inbox, *, selector, completed=False):
    journal = box.session.journal
    stream = journal.facts_stream
    route = NotificationRoute('inbox', 'capability', 'owner')
    runtime = NotificationRuntime('owner', build_catalog(), Authority(), MemoryNotificationState(),
        (SourceBinding(stream, 'execution.acceptance', 'local_snapshot', journal.facts_source),),
        (ConsumerBinding(stream.scope_id, route, 'in_process', inbox),))
    spec = SubscriptionSpec(stream.scope_id, 'capability', 'owner', (stream,), route,
        'capability.completed' if completed else 'value.accepted', 1,
        'capability_summary' if completed else 'accepted_value', 1, selector=selector)
    configure_subscription(SubscriptionChange('create', spec), runtime=runtime, context=ExecutionContext())
    configure_subscription(SubscriptionChange('enable', spec, 1), runtime=runtime, context=ExecutionContext())
    box.session.context = replace(box.session.context, bindings=(*box.session.context.bindings,
        ProviderBinding('notifications', CapabilityRequirement('notification_runtime'), 'ready', runtime)))
    return runtime, CheckpointKey(stream.scope_id, spec.subscription_id, stream)


@pytest.mark.parametrize('kind', ('command', 'operation', 'scenario', 'cascade'))
@pytest.mark.parametrize('completed', (False, True))
def test_exact_capability_subscription_matches_one_journaled_result_or_completion(kind, completed):
    declared = definitions()
    snapshot = catalog_snapshot().overlay(CatalogContribution(definitions=declared))
    target = next(definition for definition in declared if definition.kind == kind)
    selector = CapabilitySelector(target.capability_id, kind, output_name=None if completed else 'value')
    inbox = Inbox()
    with StrategyBox(capabilities=snapshot) as box:
        runtime, key = runtime_for(box, inbox, selector=selector, completed=completed)
        result = box.run(box.prepare(target), timeout=5)
        assert result.outcome == 'succeeded' and result.output('value') == 11
        notified = box.invoke('notify.required' if completed else 'notify.accepted', parameters={'key': key, 'source_run_id': result.run_id,
            'max_dispatches': 1}, timeout=5)
        assert notified.outcome == 'succeeded', notified.diagnostics
        assert len(inbox.calls) == 1
        payload = json.loads(inbox.calls[0].intent.envelope_bytes)['data']
        assert payload['capability_id'] == target.capability_id
        assert payload['capability_kind'] == kind
        if completed:
            assert payload['outcome'] == 'succeeded'
            assert 'output_name' not in payload
        else:
            assert payload['output_name'] == 'value'
            assert payload['role'] is None
            assert payload['identity_status'] == 'available'
        row, = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)
        assert row.intent.selection_evidence.capability_id == target.capability_id
        result.close()
        notified.close()


def test_scope_and_output_selector_disambiguates_reused_capability_occurrences():
    declared = definitions()
    pair = ScenarioDefinition('subscription.pair', GraphBody((
        Call('first', 'subscription.operation'), Call('second', 'subscription.operation'),
    ), {'first': OutputRef('first'), 'second': OutputRef('second')}), outputs={'first': NUMBER, 'second': NUMBER})
    snapshot = catalog_snapshot().overlay(CatalogContribution(definitions=(*declared, pair)))
    selector = CapabilitySelector('subscription.operation', 'operation', 'subscription.pair/second', 'value')
    inbox = Inbox()
    with StrategyBox(capabilities=snapshot) as box:
        _, key = runtime_for(box, inbox, selector=selector)
        result = box.invoke(pair.capability_id, timeout=5)
        notified = box.invoke('notify.accepted', parameters={'key': key, 'source_run_id': result.run_id}, timeout=5)
        assert notified.outcome == 'succeeded', notified.diagnostics
        assert len(inbox.calls) == 1
        data = json.loads(inbox.calls[0].intent.envelope_bytes)['data']
        assert data['scope_id'] == 'subscription.pair/second' and data['output_name'] == 'value'
        result.close()
        notified.close()
