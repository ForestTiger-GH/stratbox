"""Notification cursors consume confirmed contiguous coverage and atomic intent pages."""
from dataclasses import replace
import sqlite3
from types import SimpleNamespace
import pytest
from stratbox.core.notifications import MemoryNotificationState, FileNotificationState
from stratbox.core.observability.journal import MemoryJournal, JournalPage

@pytest.fixture(params=('memory','sqlite'))
def state(request,tmp_path):
    return MemoryNotificationState() if request.param=='memory' else FileNotificationState(tmp_path/'outbox')

def journal(*runs):
    source=MemoryJournal()
    for run in runs: source.append(kind='output.accepted',run_id=run,data={'value':run})
    return source

def page(source,after,through,*,run=None):
    all_facts=source.read(limit=100)
    facts=tuple(f for f in all_facts if after<f.sequence<=through and (run is None or f.run_id==run))
    return JournalPage(source.stream_id,after,through,facts,len(all_facts),filters={} if run is None else {'run_id':run})

def receipt(intent):
    return SimpleNamespace(effect_id=intent['id'],status='confirmed',kind='notification.deliver')

def test_sparse_reordered_and_duplicate_bare_facts_never_advance_checkpoint(state):
    facts=journal('one','two','three').read()
    for supplied in ((facts[0],facts[2]),(facts[1],facts[0]),(facts[0],facts[0]),(facts[1],)):
        with pytest.raises(ValueError,match='gap|reordered'): state.prepare(supplied)
        assert state.checkpoint() is None and not state.pending()
    state.prepare(facts[:1])
    with pytest.raises(ValueError,match='gap'): state.prepare(facts[2:])
    assert state.checkpoint()['sequence']==1 and len(state.pending())==1

def test_unselected_facts_certify_positions_without_creating_intents(state):
    source=journal('other','selected','other','selected');selector={'run_id':'selected'}
    assert len(state.prepare(source.read()[:3],selector=selector))==1
    assert state.checkpoint()['sequence']==3
    assert len(state.prepare(source.read(after=3),selector=selector))==1
    assert [item['payload']['fact_sequence'] for item in state.pending()]==[2,4]

def test_filtered_empty_pages_advance_the_scan_and_replay_exactly(state):
    source=journal('other','other','selected','other');selector={'run_id':'selected'}
    assert state.prepare(page(source,0,2,run='selected'),selector=selector)==()
    assert state.checkpoint()=={'sequence':2,'stream_id':source.stream_id}
    assert len(state.prepare(page(source,2,4,run='selected'),selector=selector))==1
    assert state.prepare(page(source,0,4,run='selected'),selector=selector)==()
    assert state.checkpoint()['sequence']==4

def test_reader_filter_must_be_explicitly_bound_by_subscription_selector(state):
    source=journal('A','B')
    with pytest.raises(ValueError,match='filter_not_bound'): state.prepare(page(source,0,2,run='A'))
    assert state.checkpoint() is None

def test_replay_checks_unselected_content_after_restart(state):
    facts=journal('other','selected').read();selector={'run_id':'selected'}
    state.prepare(facts,selector=selector)
    if isinstance(state,FileNotificationState): state=FileNotificationState(state.directory)
    assert state.prepare(facts,selector=selector)==()
    changed=(replace(facts[0],data={'value':'changed'}),facts[1])
    with pytest.raises(ValueError,match='content_conflict'): state.prepare(changed,selector=selector)
    assert state.checkpoint()['sequence']==2 and len(state.pending())==1

def test_replay_never_resurrects_an_acknowledged_intent(state):
    facts=journal('selected').read();intent,=state.prepare(facts)
    state.acknowledge('default',intent['id'],receipt(intent))
    assert state.prepare(facts)==() and not state.pending()
    assert state.checkpoint()['sequence']==1

def test_returned_intents_cannot_mutate_outbox_truth(state):
    intent,=state.prepare(journal('selected').read())
    with pytest.raises(TypeError): intent['payload']['data']['value']='changed'
    pending,=state.pending()
    try: pending['payload']['data']['value']='changed'
    except TypeError: pass
    assert state.pending()[0]['payload']['data']['value']=='selected'

@pytest.mark.parametrize('durable',(False,True))
def test_capacity_failure_keeps_cursor_and_pending_intents_atomic(tmp_path,durable):
    state=FileNotificationState(tmp_path/'outbox',capacity=1) if durable else MemoryNotificationState(capacity=1)
    facts=journal('one','two').read();first,=state.prepare(facts[:1])
    with pytest.raises(ValueError,match='capacity_exhausted'): state.prepare(facts[1:])
    assert state.checkpoint()['sequence']==1 and state.pending()==(first,)
    state.acknowledge('default',first['id'],receipt(first))
    assert len(state.prepare(facts[1:]))==1 and state.checkpoint()['sequence']==2

def test_sqlite_rollback_preserves_cursor_seen_positions_and_intents(tmp_path):
    state=FileNotificationState(tmp_path/'outbox');facts=journal('one','two','three').read()
    first,=state.prepare(facts[:1])
    with sqlite3.connect(state._database) as db:
        db.execute("CREATE TRIGGER reject_third BEFORE INSERT ON intents WHEN NEW.sequence=3 BEGIN SELECT RAISE(ABORT,'injected failure'); END")
    with pytest.raises(sqlite3.DatabaseError,match='injected failure'): state.prepare(facts[1:])
    restarted=FileNotificationState(state.directory)
    assert restarted.checkpoint()['sequence']==1 and restarted.pending()==(first,)
    with sqlite3.connect(state._database) as db:
        assert db.execute('SELECT sequence FROM consumed').fetchall()==[(1,)]
        db.execute('DROP TRIGGER reject_third')
    assert len(restarted.prepare(facts[1:]))==2 and restarted.checkpoint()['sequence']==3

@pytest.mark.parametrize('durable',(False,True))
def test_replay_history_has_a_global_bound_and_old_replays_expire_safely(tmp_path,durable):
    state=FileNotificationState(tmp_path/'outbox',history_limit=2) if durable else MemoryNotificationState(history_limit=2)
    facts=journal('one','two','three').read()
    state.prepare(facts,subscription_id='first');state.prepare(facts,subscription_id='second')
    if durable:
        with sqlite3.connect(state._database) as db: retained=db.execute('SELECT count(*) FROM consumed').fetchone()[0]
    else: retained=sum(len(v['seen']) for v in state._subscriptions.values())
    assert retained<=2
    with pytest.raises(ValueError,match='replay_expired'): state.prepare(facts[:1],subscription_id='first')
    assert state.checkpoint('first')['sequence']==3 and len(state.pending('first'))==3


def test_explicit_registration_starts_at_chosen_retained_floor_and_never_resets(state):
    source=journal('old','old','new','later');selector={'kind':'output.accepted'}
    state.register('following',stream_id=source.stream_id,after=2,selector=selector)
    incoming=JournalPage(source.stream_id,2,4,source.read(after=2),4,retained_after=2)
    assert len(state.prepare(incoming,subscription_id='following',selector=selector))==2
    assert state.register('following',stream_id=source.stream_id,after=2,selector=selector)['sequence']==4
    for changes in ({'stream_id':source.stream_id,'after':4},
                    {'stream_id':'another-stream','after':2}):
        with pytest.raises(ValueError,match='initial_checkpoint_conflict'):
            state.register('following',selector=selector,**changes)
    with pytest.raises(ValueError,match='initial_checkpoint_conflict'):
        state.register('following',stream_id=source.stream_id,after=2,selector={'kind':'other'})
    assert state.checkpoint('following')['sequence']==4


def test_confirmed_reader_scan_keeps_empty_filtered_prefix_progress(state):
    source=journal('other','other','selected','selected');selector={'run_id':'selected'}
    first=source.read_page(limit=1,run_id='selected',scan_limit=2)
    assert first.facts==() and first.scanned_through==2 and first.has_more
    state.prepare(first,selector=selector)
    second=source.read_page(after=first.scanned_through,limit=1,run_id='selected',scan_limit=2)
    assert len(state.prepare(second,selector=selector))==1
    assert state.checkpoint()['sequence']==3


def test_filtered_replay_cannot_omit_a_previously_selected_position(state):
    source=journal('selected','other');selector={'run_id':'selected'}
    state.prepare(source.read(),selector=selector)
    contradictory=JournalPage(source.stream_id,0,2,(),2,filters={'run_id':'selected'})
    with pytest.raises(ValueError,match='content_conflict'):
        state.prepare(contradictory,selector=selector)
    assert state.checkpoint()['sequence']==2 and len(state.pending())==1


def test_intent_identity_binds_actual_payload_and_authoritative_lookup_is_immutable(state):
    facts=journal('one').read()
    first,=state.prepare(facts)
    stored=state.intent('default',first['id'])
    assert stored==first
    with pytest.raises(TypeError): stored['route']='changed'
    other=MemoryNotificationState()
    altered=(replace(facts[0],data={'value':'different'}),)
    changed,=other.prepare(altered)
    assert changed['id']!=first['id']


def test_recovery_closes_prepare_ack_crash_window_even_after_replay_history_expiry(tmp_path):
    from stratbox.core.notifications import recover_journal_cursor
    from stratbox.core.observability.journal import FileJournal
    state=FileNotificationState(tmp_path/'outbox',history_limit=1)
    with FileJournal(tmp_path/'journal',segment_size=2) as source:
        source.register_consumer('following',after=0)
        state.register('following',stream_id=source.stream_id,after=0)
        for value in ('one','two','three'): source.append(kind='output.accepted',run_id=value)
        state.prepare(source.read_page(),subscription_id='following')
        assert state.checkpoint('following')['sequence']==3
        assert source.checkpoint().consumers['following']==0
    restarted=FileNotificationState(tmp_path/'outbox',history_limit=1)
    with FileJournal(tmp_path/'journal',segment_size=2) as source:
        partial=recover_journal_cursor(source,restarted,'following',max_pages=1,page_size=1)
        assert partial=={'sequence':1,'target':3,'complete':False}
        complete=recover_journal_cursor(source,restarted,'following',max_pages=3,page_size=1)
        assert complete['complete'] and complete['sequence']==3
        assert len(restarted.pending('following'))==3
        source.append(kind='output.accepted',run_id='four')
        page=source.read_page(after=restarted.checkpoint('following')['sequence'])
        assert len(restarted.prepare(page,subscription_id='following'))==1
        source.acknowledge('following',page)
        assert source.checkpoint().consumers['following']==4


def test_recovery_rejects_journal_acknowledgement_ahead_of_durable_state():
    from stratbox.core.notifications import recover_journal_cursor
    source=journal('one');state=MemoryNotificationState()
    state.register('following',stream_id=source.stream_id,after=0)
    source.register_consumer('following',after=0)
    source.acknowledge('following',source.read_page())
    with pytest.raises(ValueError,match='journal_ahead_of_state'):
        recover_journal_cursor(source,state,'following')
