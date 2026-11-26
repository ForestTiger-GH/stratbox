"""Journal pagination and durable dispatch keep independently scoped factual truth."""
from pathlib import Path
import json

from stratbox.core.notifications import FileNotificationState
from stratbox.core.observability.journal import FileJournal
from stratbox.sdk import StrategyBox


def test_segmented_history_cursor_and_intents_survive_restart(tmp_path):
    journal = FileJournal(tmp_path/'journal', segment_size=2)
    for index in range(9):
        journal.append(kind='output.accepted', run_id='run-a' if index % 2 else 'run-b',
            scope_id='root/selected' if index % 3 else 'root/other', command_id='command.value.encode',
            output_name='representation', data={'capability_id':'command.value.encode'})
    selector={'kind':'output.accepted', 'run_id':'run-a', 'scope_id':'root/selected'}
    state=FileNotificationState(tmp_path/'dispatch')
    after=0; selected=[]
    while True:
        page=journal.read(after=after,limit=2)
        if not page: break
        selected.extend(state.prepare(page,subscription_id='selected',selector=selector,route='local'))
        after=page[-1].sequence
    assert len(selected)==3
    restored=FileNotificationState(tmp_path/'dispatch')
    assert restored.pending('selected')==tuple(selected)
    reopened=FileJournal(tmp_path/'journal',segment_size=2)
    assert len(reopened.read(limit=100))==9
    assert restored.prepare(reopened.read(limit=100),subscription_id='selected',selector=selector,route='local')==()
    assert len(list((tmp_path/'journal').glob('facts-*.jsonl')))==5


def test_composite_subscription_can_select_exact_callable_and_scope():
    from stratbox.capabilities.catalog import standard_catalog
    from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, InputRef, OutputRef, PortContract
    operation=OperationDefinition('operation.test.encode', inputs={'value':PortContract('value')},
        outputs={'representation':PortContract('representation')},
        body=GraphBody((Call('encode','command.value.encode',{'value':InputRef('value')}),),
            {'representation':OutputRef('encode','representation')}))
    with StrategyBox(catalog=standard_catalog().with_definitions(operation)) as box:
        result=box.invoke(operation.id,inputs={'value':{'metric':'x','value':0}})
        assert result.outcome=='succeeded',result.diagnostics
        facts=box.session.journal.read(run_id=result.run_id)
        completion=[fact for fact in facts if fact.kind=='scope.completed' and fact.data.get('capability_id')==operation.id]
        assert len(completion)==1 and completion[0].scope_id=='root'
        accepted=[fact for fact in facts if fact.kind=='output.accepted' and fact.data.get('capability_id')==operation.id]
        assert any(fact.scope_id=='root' and fact.output_name=='representation' for fact in accepted)


import pytest


@pytest.mark.parametrize('acknowledgement',(None,False,{}, {'status':'rejected'},{'status':'unknown'}))
def test_notification_without_positive_acknowledgement_cannot_confirm_delivery(acknowledgement):
    class Provider:
        scope_id="fixture.notifications.provider"
        def deliver(self,intent): return acknowledgement
    intent={'id':'one-effect','route':'one-channel','payload':{'text':'test'}}
    with StrategyBox(providers={'notification':Provider()}) as box:
        result=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert result.effects[intent['id']].status!='confirmed'
        assert result.outcome!='succeeded'


@pytest.mark.parametrize('lookup',(False,{'status':'rejected'},{'status':'unknown'},
    {'status':'confirmed','effect_id':'another-effect'},
    {'status':'confirmed','effect_kind':'storage.write'}))
def test_negative_lookup_cannot_reconcile_unknown_delivery(lookup):
    class Provider:
        scope_id="fixture.notifications.provider"
        calls=0
        def deliver(self,intent):
            self.calls+=1
            raise OSError('acknowledgement lost')
        def lookup(self,identity):return lookup
    provider=Provider();intent={'id':'uncertain-effect','route':'one-channel','payload':{}}
    with StrategyBox(providers={'notification':provider}) as box:
        first=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert first.outcome=='unknown'
        second=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert second.effects[intent['id']].status!='confirmed'
        assert provider.calls==1


def test_acknowledgement_evidence_is_a_snapshot_of_the_actual_handoff():
    acknowledgement={'status':'confirmed','message_id':'original'}
    class Provider:
        scope_id="fixture.notifications.provider"
        def deliver(self,intent):return acknowledgement
    intent={'id':'immutable-ack','route':'one-channel','payload':{}}
    with StrategyBox(providers={'notification':Provider()}) as box:
        result=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert result.outcome=='succeeded'
        acknowledgement['message_id']='changed later'
        assert result.effects[intent['id']].value['message_id']=='original'


@pytest.mark.parametrize('durable',(False,True))
def test_confirmed_handoff_closes_pending_intent_and_frees_capacity(tmp_path,durable):
    from stratbox.core.notifications import MemoryNotificationState
    state=FileNotificationState(tmp_path/'state') if durable else MemoryNotificationState(capacity=2)
    journal=FileJournal(tmp_path/'source')
    for index in range(2):journal.append(kind='output.accepted',run_id='source-'+str(index))
    class Channel:
        scope_id="fixture.notifications.channel"
        calls=0
        def deliver(self,intent):
            self.calls+=1
            return {'status':'accepted','message_id':str(self.calls)}
    channel=Channel();parameters={'subscription_id':'source','selector':{'kind':'output.accepted'},'route':'channel'}
    facts=journal.read(limit=10)
    with StrategyBox(providers={'notification_state':state,'notification':channel}) as box:
        prepared=box.invoke('command.notification.prepare',inputs={'facts':facts},parameters=parameters)
        assert prepared.outcome=='succeeded',prepared.diagnostics
        for intent in prepared.output('intents'):
            delivered=box.invoke('command.notification.deliver',inputs={'intent':intent})
            assert delivered.outcome=='succeeded',delivered.diagnostics
        assert not state.pending('source') and channel.calls==2
        # Replaying the same facts and transaction must read the current queue.
        repeated=box.invoke('command.notification.prepare',inputs={'facts':facts},parameters=parameters)
        assert repeated.outcome=='succeeded' and repeated.output('intents')==()
        journal.append(kind='output.accepted',run_id='later')
        later=box.invoke('command.notification.prepare',inputs={'facts':journal.read(after=2)},parameters=parameters)
        assert later.outcome=='succeeded' and len(later.output('intents'))==1


def test_prepare_resumes_an_unknown_pending_handoff_without_new_facts(tmp_path):
    from stratbox.core.notifications import MemoryNotificationState
    state=MemoryNotificationState();journal=FileJournal(tmp_path/'source')
    journal.append(kind='output.accepted',run_id='source')
    class Channel:
        scope_id="fixture.notifications.channel"
        calls=0
        def deliver(self,intent):self.calls+=1;raise OSError('ack lost')
        def lookup(self,identity):return None
    channel=Channel();parameters={'subscription_id':'source','route':'channel'}
    with StrategyBox(providers={'notification_state':state,'notification':channel}) as box:
        intent,=box.invoke('command.notification.prepare',inputs={'facts':journal.read()},parameters=parameters).output('intents')
        first=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert first.outcome=='unknown' and len(state.pending('source'))==1
        resumed=box.invoke('command.notification.prepare',inputs={'facts':()},parameters=parameters)
        assert resumed.outcome=='succeeded' and resumed.output('intents')==(intent,)
        again=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert again.outcome=='unknown' and channel.calls==1


def test_persisted_cursor_rejects_a_replaced_journal_stream(tmp_path):
    from stratbox.core.observability.journal import MemoryJournal
    first=MemoryJournal();first.append(kind='output.accepted',run_id='before')
    state=FileNotificationState(tmp_path/'state')
    state.prepare(first.read(),subscription_id='source')
    replacement=MemoryJournal();replacement.append(kind='output.accepted',run_id='after')
    with pytest.raises(ValueError,match='stream'):
        FileNotificationState(tmp_path/'state').prepare(replacement.read(),subscription_id='source')
    assert len(state.pending('source'))==1


def test_default_subscription_excludes_notification_wrapper_feedback(tmp_path):
    from stratbox.capabilities.catalog import standard_catalog
    from stratbox.capabilities.model import CommandDefinition, OperationDefinition, PortContract, MethodRef, Call, GraphBody, InputRef, OutputRef
    from stratbox.core.notifications import MemoryNotificationState
    command=CommandDefinition('command.custom.handoff',inputs={'intent':PortContract('intent')},
        outputs={'receipt':PortContract('receipt')},method=MethodRef('stratbox.core.commands.notifications:notification_deliver'),
        effects=frozenset({'notification.deliver'}),required_providers=frozenset({'notification'}))
    operation=OperationDefinition('operation.custom.handoff',inputs=command.inputs,outputs=command.outputs,
        body=GraphBody((Call('send',command.id,{'intent':InputRef('intent')}),),{'receipt':OutputRef('send','receipt')}))
    class Channel:
        scope_id="fixture.notifications.channel"
        def deliver(self,intent):return {'status':'confirmed'}
    state=MemoryNotificationState()
    with StrategyBox(catalog=standard_catalog().with_definitions(command,operation),providers={'notification':Channel()}) as box:
        result=box.invoke(operation.id,inputs={'intent':{'id':'notice','route':'channel','payload':{}}})
        assert result.outcome=='succeeded',result.diagnostics
        facts=box.session.journal.read(run_id=result.run_id)
        assert state.prepare(facts,subscription_id='default',selector={'kind':'output.accepted'})==()
        explicit=state.prepare(facts,subscription_id='monitor-handoff',selector={'kind':'output.accepted','origin':'notification'})
        assert explicit
