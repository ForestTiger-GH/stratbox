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
