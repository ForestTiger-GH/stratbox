from dataclasses import replace
import json

from stratbox.core.execution import Correlation
from stratbox.core.notifications import CheckpointKey, PrepareRequest, SourceBinding, SubscriptionChange, configure_subscription, prepare
from stratbox.core.observability import FieldSchemaRegistry, JournalReadLimits, OrchestrationJournal, decode_record, encode_record
from stratbox.shared.identity import ByteIdentity


def test_stage_facts_survive_diagnostic_eviction_and_independent_subscriber_cursors(session):
    runtime, _, context, _, _, old_spec = session
    journal = OrchestrationJournal('public', max_records=1)
    runtime = replace(runtime, sources=(SourceBinding(journal.facts_stream, 'execution.acceptance',
                                                     'local_snapshot', journal.facts_source),))
    fields = frozenset({'value_id', 'stage', 'role', 'identity', 'source_id', 'qualification', 'complete', 'acceptance_id'})
    runtime.authority.fields = fields
    for subscription_id in ('a', 'b'):
        spec = replace(old_spec, subscription_id=subscription_id, streams=(journal.facts_stream,),
                       topic_id='value.accepted', projection_id='accepted_value')
        configure_subscription(SubscriptionChange('create', spec), runtime=runtime, context=context)
        configure_subscription(SubscriptionChange('enable', spec, 1), runtime=runtime, context=context)
    correlation = Correlation(session_id='public', run_id='run', task_id='extract', command_id='fields.interpret', work_id='decode')
    records = []
    # A -> B -> A are three accepted transitions, including a return to an
    # earlier byte identity. Per-acceptance identity prevents accidental loss.
    for position, value in enumerate((b'A', b'B', b'A')):
        records.append(journal.accepted_value(correlation, value_id='extract', stage='extract', role='extracts',
            identity=ByteIdentity.of(value), acceptance_id='acceptance.' + str(position)))
    assert len(journal.records) == 1
    assert journal.facts_source.pending == 3
    assert decode_record(encode_record(records[0])).correlation == correlation
    FieldSchemaRegistry().validate(records[0])
    first = prepare(PrepareRequest(CheckpointKey('public', 'a', journal.facts_stream)), runtime=runtime, context=context)
    assert first.outcome == 'succeeded'
    assert first.value.prepared == 3
    assert prepare(PrepareRequest(CheckpointKey('public', 'a', journal.facts_stream)), runtime=runtime, context=context).value.prepared == 0
    second = prepare(PrepareRequest(CheckpointKey('public', 'b', journal.facts_stream)), runtime=runtime, context=context)
    assert second.value.prepared == 3
    rows = runtime.state.scan_dispatches('public', 'b', limit=10)
    assert {json.loads(row.intent.envelope_bytes)['data']['acceptance_id'] for row in rows} == {'acceptance.0', 'acceptance.1', 'acceptance.2'}


def test_accepted_publication_retry_is_idempotent_and_has_complete_identity():
    journal = OrchestrationJournal('session')
    correlation = Correlation(session_id='session', run_id='run', task_id='task')
    options = dict(value_id='value', stage='extract', role='extracts', identity=ByteIdentity.of(b'A'))
    record = journal.accepted_value(correlation, **options)
    assert journal.accepted_value(correlation, **options) == record
    head = journal.facts_source.head(journal.facts_stream)
    page = journal.facts_source.read_page(head.cursor(0), head=head, limits=JournalReadLimits())
    assert [entry.record for entry in page.entries] == [record]
    assert record.payload['identity']['sha256'] == ByteIdentity.of(b'A').sha256


def test_confirmed_destination_fact_is_independent_and_notification_effects_do_not_recurse(session):
    from stratbox.core.execution.contracts import EffectReceipt
    from stratbox.core.notifications import DeliverRequest, deliver
    runtime, _, context, _, inbox, old_spec = session
    journal = OrchestrationJournal('public', max_records=1)
    runtime = replace(runtime, sources=(SourceBinding(journal.facts_stream, 'execution.acceptance',
                                                     'local_snapshot', journal.facts_source),))
    runtime.authority.fields = frozenset({'effect_id', 'effect_kind', 'state', 'identity', 'destination_id', 'guarantee', 'stage'})
    spec = replace(old_spec, subscription_id='effects', streams=(journal.facts_stream,),
                   topic_id='effect.confirmed', projection_id='confirmed_effect')
    configure_subscription(SubscriptionChange('create', spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange('enable', spec, 1), runtime=runtime, context=context)
    correlation = Correlation(session_id='public', run_id='run', task_id='save')
    receipt = EffectReceipt('storage.write', 'confirmed', effect_id='save', reference='/private/output/file.csv',
                            identity=ByteIdentity.of(b'csv'), guarantee='atomic_create')
    fact = journal.confirmed_effect(correlation, receipt)
    assert '/private/' not in encode_record(fact).decode()
    assert fact.correlation.effect_id == 'save'
    assert journal.confirmed_effect(correlation, receipt) == fact
    key = CheckpointKey('public', 'effects', journal.facts_stream)
    assert prepare(PrepareRequest(key), runtime=runtime, context=context).value.prepared == 1
    row, = runtime.state.scan_dispatches('public', 'effects', limit=10)
    result = deliver(DeliverRequest('public', row.intent.dispatch_id), runtime=runtime, context=context)
    assert result.outcome == 'succeeded'
    assert len(inbox.calls) == 1
    assert journal.confirmed_effect(correlation, EffectReceipt('notification.handoff', 'confirmed', effect_id='send')) is None
    assert journal.facts_source.pending == 1
