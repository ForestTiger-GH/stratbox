"""Standard notification actions preserve authoritative intent and transaction truth."""
from dataclasses import replace
import pytest
from stratbox.core.notifications import MemoryNotificationState, FileNotificationState
from stratbox.core.observability.journal import MemoryJournal
from stratbox.sdk import StrategyBox

class Channel:
    scope_id="fixture.notifications.channel"
    def __init__(self): self.calls=[]
    def deliver(self,intent):
        self.calls.append(intent)
        return {'status':'confirmed','effect_id':intent['id']}

def facts(*runs):
    journal=MemoryJournal()
    for run in runs: journal.append(kind='output.accepted',run_id=run,data={'value':run})
    return journal,journal.read()

@pytest.mark.parametrize('durable',(False,True))
@pytest.mark.parametrize('change',('payload','route'))
def test_subscribed_intent_tampering_is_rejected_before_channel(tmp_path,durable,change):
    state=FileNotificationState(tmp_path/'state') if durable else MemoryNotificationState()
    _,source=facts('source');intent,=state.prepare(source,route='channel')
    mutated={**intent}
    if change=='route': mutated['route']='another-channel'
    else: mutated['payload']={**intent['payload'],'data':{'value':'tampered'}}
    channel=Channel()
    with StrategyBox(providers={'notification_state':state,'notification':channel}) as box:
        result=box.invoke('command.notification.deliver',inputs={'intent':mutated})
        assert result.outcome=='failed' and not channel.calls
        assert state.pending()==(intent,)


def test_confirmed_delivery_retry_after_pending_retirement_never_sends_again():
    state=MemoryNotificationState();_,source=facts('source');intent,=state.prepare(source)
    channel=Channel()
    with StrategyBox(providers={'notification_state':state,'notification':channel}) as box:
        first=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert first.outcome=='succeeded',first.diagnostics
        assert not state.pending()
        repeated=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert repeated.outcome=='succeeded',repeated.diagnostics
        assert len(channel.calls)==1


def test_manual_intent_cannot_reuse_a_confirmed_effect_for_different_content():
    channel=Channel();intent={'id':'explicit','route':'channel','payload':{'value':'original'}}
    with StrategyBox(providers={'notification':channel}) as box:
        assert box.invoke('command.notification.deliver',inputs={'intent':intent}).outcome=='succeeded'
        changed={**intent,'payload':{'value':'changed'}}
        rejected=box.invoke('command.notification.deliver',inputs={'intent':changed})
        assert rejected.outcome=='failed' and len(channel.calls)==1


def test_sequence_gap_is_a_rejected_state_transaction_not_an_unknown_write():
    state=MemoryNotificationState();_,source=facts('one','two')
    with StrategyBox(providers={'notification_state':state}) as box:
        result=box.invoke('command.notification.prepare',inputs={'facts':source[1:]})
        assert result.outcome=='failed',result.diagnostics
        assert any('state_rejected' in code for code in result.diagnostics)
        assert state.checkpoint() is None and not state.pending()


def test_conflicting_replay_content_cannot_bypass_cached_state_effect():
    state=MemoryNotificationState();_,source=facts('one')
    with StrategyBox(providers={'notification_state':state}) as box:
        assert box.invoke('command.notification.prepare',inputs={'facts':source}).outcome=='succeeded'
        changed=(replace(source[0],data={'value':'changed'}),)
        result=box.invoke('command.notification.prepare',inputs={'facts':changed})
        assert result.outcome=='failed',result.diagnostics
        assert state.checkpoint()['sequence']==1 and len(state.pending())==1


def test_preparation_capacity_rejection_can_retry_after_confirmed_delivery():
    state=MemoryNotificationState(capacity=1);_,source=facts('one','two');channel=Channel()
    with StrategyBox(providers={'notification_state':state,'notification':channel}) as box:
        first=box.invoke('command.notification.prepare',inputs={'facts':source[:1]})
        intent,=first.output('intents')
        rejected=box.invoke('command.notification.prepare',inputs={'facts':source[1:]})
        assert rejected.outcome=='failed'
        assert box.invoke('command.notification.deliver',inputs={'intent':intent}).outcome=='succeeded'
        retried=box.invoke('command.notification.prepare',inputs={'facts':source[1:]})
        assert retried.outcome=='succeeded',retried.diagnostics
        assert state.checkpoint()['sequence']==2 and len(state.pending())==1


def test_standard_preparation_consumes_filtered_page_coverage():
    state=MemoryNotificationState();journal,_=facts('other','other','selected')
    selector={'run_id':'selected'}
    with StrategyBox(providers={'notification_state':state}) as box:
        empty=journal.read_page(run_id='selected',scan_limit=2)
        first=box.invoke('command.notification.prepare',inputs={'page':empty},parameters={'selector':selector})
        assert first.outcome=='succeeded' and first.output('intents')==()
        assert state.checkpoint()['sequence']==2
        next_page=journal.read_page(after=2,run_id='selected')
        second=box.invoke('command.notification.prepare',inputs={'page':next_page},parameters={'selector':selector})
        assert second.outcome=='succeeded' and len(second.output('intents'))==1
        assert state.checkpoint()['sequence']==3


def test_channel_scope_is_required_before_handoff():
    class Unscoped:
        calls=0
        def deliver(self,intent):self.calls+=1;return {'status':'confirmed'}
    channel=Unscoped()
    with StrategyBox(providers={'notification':channel}) as box:
        result=box.invoke('command.notification.deliver',inputs={'intent':{'id':'unscoped','payload':{}}})
        assert result.outcome=='failed' and not channel.calls
        assert any('channel_scope_required' in code for code in result.diagnostics)


def test_binding_scope_survives_unwrapping_and_blocks_foreign_channel_reuse():
    from stratbox.core.runtime.capabilities import ProviderBinding,CapabilityRequirement
    channel=Channel();requirement=CapabilityRequirement('notification')
    first=ProviderBinding('channel',requirement,'ready',channel,'account-a')
    second=ProviderBinding('channel',requirement,'ready',channel,'account-b')
    intent={'id':'scoped','route':'channel','payload':{'value':'one'}}
    with StrategyBox(providers={'notification':first}) as box:
        assert box.invoke('command.notification.deliver',inputs={'intent':intent}).outcome=='succeeded'
        box.session.providers['notification']=second
        rejected=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert rejected.outcome=='failed' and len(channel.calls)==1
        assert not rejected.effects


def test_natural_command_output_selector_creates_one_intent_per_acceptance():
    with StrategyBox() as box:
        source=box.invoke('command.value.encode',inputs={'value':7})
        assert source.outcome=='succeeded'
        page=box.session.journal.read_page(run_id=source.run_id)
        prepared=box.invoke('command.notification.prepare',inputs={'page':page},parameters={
            'selector':{'run_id':source.run_id,'kind':'output.accepted',
                'capability_id':'command.value.encode','scope_id':'root','output_name':'representation'}})
        assert prepared.outcome=='succeeded',prepared.diagnostics
        assert len(prepared.output('intents'))==1


def test_reconciliation_uses_authoritative_intent_and_rejects_foreign_channel_before_lookup():
    class Uncertain:
        def __init__(self,scope): self.scope_id=scope;self.lookups=0
        def deliver(self,intent): raise OSError('acknowledgement lost')
        def lookup(self,identity):
            self.lookups+=1
            return {'status':'confirmed','effect_id':identity}
    first=Uncertain('account-a');foreign=Uncertain('account-b')
    intent={'id':'reconcile-scoped','route':'channel','payload':{'value':'one'}}
    with StrategyBox(providers={'notification':first}) as box:
        delivered=box.invoke('command.notification.deliver',inputs={'intent':intent})
        assert delivered.outcome=='unknown'
        receipt=delivered.effects[intent['id']]
        box.session.providers['notification']=foreign
        rejected=box.invoke('command.notification.reconcile',inputs={'receipt':receipt})
        assert rejected.outcome=='failed' and foreign.lookups==0
        assert box.session.lookup_effect(intent['id']).status=='unknown'
        box.session.providers['notification']=first
        forged=replace(receipt,kind='storage.write',resource='wrong',intent={'id':intent['id'],'route':'wrong'})
        recovered=box.invoke('command.notification.reconcile',inputs={'receipt':forged})
        assert recovered.outcome=='succeeded',recovered.diagnostics
        assert recovered.output('assessment').status=='confirmed' and first.lookups==1


def test_reconciliation_cannot_confirm_a_non_notification_effect():
    from stratbox.core.execution.service import EffectReceipt
    class Lookup(Channel):
        def __init__(self):super().__init__();self.lookups=0
        def lookup(self,identity):self.lookups+=1;return {'status':'confirmed','effect_id':identity}
    channel=Lookup()
    with StrategyBox(providers={'notification':channel}) as box:
        authoritative=EffectReceipt('foreign-kind','storage.write','unknown',resource='storage',intent={'id':'foreign-kind'})
        box.session._save_effect(authoritative)
        forged=replace(authoritative,kind='notification.deliver')
        result=box.invoke('command.notification.reconcile',inputs={'receipt':forged})
        assert result.outcome=='failed' and not channel.lookups
