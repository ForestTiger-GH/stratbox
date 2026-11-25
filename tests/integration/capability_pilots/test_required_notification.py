"""A prepared graph owns a real save fact, intent and required handoff."""
from dataclasses import replace
from datetime import datetime, timezone

from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
from stratbox.capabilities.commands import MATERIAL_INPUT, REPRESENTATION, RECEIPT
from stratbox.capabilities.commands.notifications import HANDOFFS
from stratbox.core.execution import ExecutionContext
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.notifications import (
    AccessDecision, CheckpointKey, ConsumerBinding, HandoffReceipt, MemoryNotificationState,
    NotificationRoute, NotificationRuntime, SourceBinding, SubscriptionChange, SubscriptionSpec,
    build_catalog, configure_subscription,
)
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox


class Authority:
    def authorize(self, request):
        return AccessDecision('allow', frozenset({'effect_id', 'effect_kind', 'state', 'identity',
            'destination_id', 'guarantee', 'stage'}), frozenset({'event_ref', 'occurred_at_utc'}), 'grant', 'route.1')


class Inbox:
    def __init__(self, *, lost=False):
        self.calls = []
        self.receipts = {}
        self.lost = lost
    def accept(self, handoff):
        lookup = handoff.lookup
        self.calls.append(handoff)
        receipt = HandoffReceipt(lookup.dispatch_id, lookup.attempt_id, lookup.route,
            lookup.route_revision, lookup.payload_identity, 'accepted', datetime.now(timezone.utc), evidence_ref='proof')
        self.receipts[lookup.attempt_id] = receipt
        if self.lost:
            raise TimeoutError('consumer accepted, reply lost')
        return receipt
    def lookup(self, request):
        return self.receipts.get(request.attempt_id)


def notification_runtime(box, inbox):
    journal = box.session.journal
    stream = journal.facts_stream
    route = NotificationRoute('inbox', 'saved', 'owner')
    runtime = NotificationRuntime('owner', build_catalog(), Authority(), MemoryNotificationState(),
        (SourceBinding(stream, 'execution.acceptance', 'local_snapshot', journal.facts_source),),
        (ConsumerBinding(stream.scope_id, route, 'in_process', inbox),))
    spec = SubscriptionSpec(stream.scope_id, 'saved', 'owner', (stream,), route,
                            'effect.confirmed', 1, 'confirmed_effect', 1)
    context = ExecutionContext()
    configure_subscription(SubscriptionChange('create', spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange('enable', spec, 1), runtime=runtime, context=context)
    box.session.context = replace(box.session.context, bindings=(*box.session.context.bindings,
        ProviderBinding('notifications', CapabilityRequirement('notification_runtime'), 'ready', runtime)))
    return runtime, CheckpointKey(stream.scope_id, spec.subscription_id, stream)


def workflow(key):
    return ScenarioDefinition('fixture.saved_notification', GraphBody((
        Call('extract', 'extract.observations', {'material': InputRef('material')}, profile_id='fixture.debt'),
        Call('view', 'view.table', {'observations': OutputRef('extract', 'observations')}),
        Call('render', 'render.table', {'view': OutputRef('view', 'view')}),
        Call('save', 'save.product', {'material': OutputRef('render', 'representation')}, {'destination': 'debt.csv'}),
        Call('notify', 'notify.saved', {'effect': OutputRef('save', 'receipt')}, {'key': key}),
    ), {'representation': OutputRef('render', 'representation'), 'handoffs': OutputRef('notify', 'handoffs')},
        required_effects=('save', 'notify')), inputs={'material': MATERIAL_INPUT},
        outputs={'representation': REPRESENTATION, 'handoffs': HANDOFFS},
        effects=frozenset({'storage.write', 'notification.state_commit', 'notification.handoff'}))


def test_prepared_plan_requires_real_fact_intent_and_handoff(profiled_catalog, two_tables, tmp_path):
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))},
                     settings=ExecutionSettings(max_workers=1)) as box:
        runtime, key = notification_runtime(box, inbox)
        plan = box.prepare(workflow(key), inputs={'material': two_tables})
        assert any(task.operation_id == 'notification.handoff' for task in plan.tasks)
        result = box.run(plan, timeout=15)
        assert result.outcome == 'succeeded', result.diagnostics
        assert (tmp_path / 'debt.csv').read_bytes() == result.output('representation').data
        assert len(inbox.calls) == 1
        assert result.output('handoffs')[0].state == 'consumer_accepted'
        assert any(effect.kind == 'notification.handoff' and effect.state == 'confirmed' for effect in result.effects)
        row, = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)
        assert row.state == 'consumer_accepted'
        # Handoff acceptance has no fabricated external-channel delivery receipt.
        assert all(effect.guarantee != 'channel_delivery' for effect in result.effects)


def test_unknown_required_handoff_keeps_saved_product_and_reconciles_without_second_send(profiled_catalog, two_tables, tmp_path):
    inbox = Inbox(lost=True)
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))},
                     settings=ExecutionSettings(max_workers=1)) as box:
        runtime, key = notification_runtime(box, inbox)
        result = box.invoke(workflow(key), inputs={'material': two_tables}, timeout=15)
        assert result.outcome == 'unknown'
        assert result.scopes['fixture.saved_notification/save'] == 'succeeded'
        material = result.scope_outputs['fixture.saved_notification/render']['representation']
        assert (tmp_path / 'debt.csv').read_bytes() == material.data
        assert len(inbox.calls) == 1
        row, = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)
        assert row.state == 'unknown'
        reconciled = box.invoke('notify.reconcile', parameters={'key': key}, timeout=10)
        assert reconciled.outcome == 'succeeded', reconciled.diagnostics
        assert reconciled.output('handoffs')[0].state == 'consumer_accepted'
        assert len(inbox.calls) == 1


def test_prior_unrelated_fact_cannot_satisfy_current_run_required_handoff(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        _, key = notification_runtime(box, inbox)
        material = Representation('csv', 1, 'text/csv', b'value\n1')
        saved = box.invoke('save.product', inputs={'material': material}, parameters={'destination': 'prior.csv'}, timeout=5)
        assert saved.outcome == 'succeeded'
        unrelated = box.invoke('notify.required', parameters={'key': key}, timeout=5)
        assert unrelated.outcome == 'failed'
        assert 'notification.required_intent_missing' in unrelated.diagnostics
        assert inbox.calls == []
        exact = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')}, parameters={'key': key}, timeout=5)
        assert exact.outcome == 'succeeded', exact.diagnostics
        assert len(inbox.calls) == 1


def test_required_dispatch_selection_scans_all_history_pages(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        _, key = notification_runtime(box, inbox)
        results = []
        for i in range(2):
            material = Representation('csv', 1, 'text/csv', ('value\n' + str(i)).encode())
            results.append(box.invoke('save.product', inputs={'material': material},
                parameters={'destination': 'saved.' + str(i) + '.csv'}, timeout=5))
        first = box.invoke('notify.required', parameters={'key': key, 'source_run_id': results[0].run_id,
            'max_dispatches': 1}, timeout=5)
        assert first.outcome == 'succeeded', first.diagnostics
        assert first.output('prepared').next_position is None
        assert first.output('prepared').complete
        second = box.invoke('notify.required', parameters={'key': key, 'source_run_id': results[1].run_id,
            'max_dispatches': 1}, timeout=5)
        assert second.outcome == 'succeeded', second.diagnostics
        assert second.output('prepared').next_position is None
        assert len(inbox.calls) == 2


def test_completed_dispatch_evidence_survives_acknowledged_source_release(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        runtime, key = notification_runtime(box, inbox)
        for i in range(3):
            material = Representation('csv', 1, 'text/csv', ('value\n' + str(i)).encode())
            saved = box.invoke('save.product', inputs={'material': material},
                parameters={'destination': 'saved.' + str(i) + '.csv'}, timeout=5)
            delivered = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')},
                parameters={'key': key, 'max_dispatches': 1}, timeout=5)
            assert delivered.outcome == 'succeeded', delivered.diagnostics
            assert len(inbox.calls) == i + 1
            facts = box.session.journal.facts_source
            facts.acknowledge(facts.head(box.session.journal.facts_stream).tail_offset)
            saved.close()
            delivered.close()
        assert all(row.state == 'consumer_accepted' for row in runtime.state.scan_dispatches(
            key.scope_id, key.subscription_id, limit=10))


def test_required_set_larger_than_page_is_complete_and_small_scan_budget_never_succeeds(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        runtime, key = notification_runtime(box, inbox)
        material = Representation('csv', 1, 'text/csv', b'value\n1')
        definition = ScenarioDefinition('fixture.multiple_saves', GraphBody(tuple(
            Call('save' + str(i), 'save.product', {'material': material}, {'destination': 'batch.' + str(i) + '.csv'})
            for i in range(3)), {str(i): OutputRef('save' + str(i), 'receipt') for i in range(3)}),
            outputs={str(i): RECEIPT for i in range(3)},
            effects=frozenset({'storage.write'}))
        saved = box.invoke(definition, timeout=5)
        assert saved.outcome == 'succeeded'
        incomplete = box.invoke('notify.required', parameters={'key': key, 'source_run_id': saved.run_id,
            'max_dispatches': 1, 'max_scan_pages': 1}, timeout=5)
        assert incomplete.outcome == 'failed'
        assert not inbox.calls
        assert any(d.code == 'notification.required_selection_incomplete'
            for result in incomplete.results.values() for d in result.diagnostics)
        delivered = box.invoke('notify.required', parameters={'key': key, 'source_run_id': saved.run_id,
            'max_dispatches': 1}, timeout=5)
        assert delivered.outcome == 'succeeded', delivered.diagnostics
        assert len(delivered.output('prepared').dispatch_ids) == 3
        assert len(delivered.output('handoffs')) == len(inbox.calls) == 3
        rows = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)
        assert len(rows) == 3 and all(row.state == 'consumer_accepted' for row in rows)


def test_explicit_required_dispatch_set_cannot_succeed_when_one_identity_is_missing(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        _, key = notification_runtime(box, inbox)
        saved = box.invoke('save.product', inputs={'material': Representation('csv', 1, 'text/csv', b'1')},
            parameters={'destination': 'exact.csv'}, timeout=5)
        prepared = box.invoke('notification.prepare_intents', parameters={'key': key, 'source_run_id': saved.run_id}, timeout=5)
        dispatch_id, = prepared.output('value').dispatch_ids
        incomplete = box.invoke('notify.required', parameters={'key': key, 'source_run_id': saved.run_id,
            'dispatch_ids': (dispatch_id, 'missing-dispatch'), 'max_dispatches': 1}, timeout=5)
        assert incomplete.outcome == 'failed' and not inbox.calls
        assert any(d.code == 'notification.required_intent_missing'
            for result in incomplete.results.values() for d in result.diagnostics)
        delivered = box.invoke('notify.required', parameters={'key': key, 'source_run_id': saved.run_id,
            'dispatch_ids': (dispatch_id,), 'max_dispatches': 1}, timeout=5)
        assert delivered.outcome == 'succeeded' and len(inbox.calls) == 1
        repeated = box.invoke('notify.required', parameters={'key': key, 'source_run_id': saved.run_id,
            'dispatch_ids': (dispatch_id,)}, timeout=5)
        assert repeated.outcome == 'succeeded' and len(inbox.calls) == 1


def test_unknown_handoff_reconciles_after_source_acknowledgement_without_resend(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox(lost=True)
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        runtime, key = notification_runtime(box, inbox)
        saved = box.invoke('save.product', inputs={'material': Representation('csv', 1, 'text/csv', b'1')},
            parameters={'destination': 'unknown.csv'}, timeout=5)
        unknown = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')}, parameters={'key': key}, timeout=5)
        assert unknown.outcome == 'unknown' and len(inbox.calls) == 1
        facts = box.session.journal.facts_source
        checkpoint = runtime.state.get_checkpoint(key)
        facts.acknowledge(checkpoint.last_offset)
        recovered = box.invoke('notify.reconcile', parameters={'key': key, 'max_dispatches': 1}, timeout=5)
        assert recovered.outcome == 'succeeded', recovered.diagnostics
        assert len(inbox.calls) == 1
        row, = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)
        assert row.state == 'consumer_accepted'


def test_explicit_run_selection_intersects_exact_saved_receipt(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        _, key = notification_runtime(box, inbox)
        saved = box.invoke('save.product', inputs={'material': Representation('csv', 1, 'text/csv', b'1')},
            parameters={'destination': 'intersection.csv'}, timeout=5)
        rejected = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')},
            parameters={'key': key, 'source_run_id': 'different-run'}, timeout=5)
        assert rejected.outcome == 'failed' and not inbox.calls
        delivered = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')},
            parameters={'key': key, 'source_run_id': saved.run_id}, timeout=5)
        assert delivered.outcome == 'succeeded' and len(inbox.calls) == 1


def test_required_preparation_budget_never_hands_off_a_caught_up_prefix(profiled_catalog, tmp_path):
    from stratbox.shared.data.representation import Representation
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': LocalFileStore(str(tmp_path))}) as box:
        _, key = notification_runtime(box, inbox)
        saved = box.invoke('save.product', inputs={'material': Representation('csv', 1, 'text/csv', b'1')},
            parameters={'destination': 'preparation-bound.csv'}, timeout=5)
        incomplete = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')},
            parameters={'key': key, 'max_dispatches': 1, 'max_pages': 1}, timeout=5)
        assert incomplete.outcome == 'failed' and not inbox.calls
        assert any(d.code == 'notification.required_preparation_incomplete'
            for result in incomplete.results.values() for d in result.diagnostics)
        completed = box.invoke('notify.saved', inputs={'effect': saved.output('receipt')},
            parameters={'key': key, 'max_dispatches': 1}, timeout=5)
        assert completed.outcome == 'succeeded' and len(inbox.calls) == 1


def test_accepted_operation_rejects_a_confirmed_effect_subscription_before_preparation(profiled_catalog):
    inbox = Inbox()
    with StrategyBox(capabilities=profiled_catalog) as box:
        runtime, key = notification_runtime(box, inbox)
        before = runtime.state.get_checkpoint(key)
        result = box.invoke('notify.accepted', parameters={'key': key}, timeout=5)
        assert result.outcome == 'failed' and not inbox.calls
        assert runtime.state.get_checkpoint(key) == before
        assert any(d.code == 'notification.required_topic_mismatch'
            for value in result.results.values() for d in value.diagnostics)
