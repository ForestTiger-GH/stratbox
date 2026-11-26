"""Admission owns bounded immutable plans before publishing any accepted run."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pandas as pd
import pytest

from stratbox.capabilities.model import MethodRef,PortContract,ReuseContract
from stratbox.capabilities.plan.models import BoundCommand,CommandTask,MapTask,PreparedPlan,TemplateInput,ValueRef
from stratbox.core.execution.service import ExecutionService,ExecutionSettings,ExecutionFailure

ENTERED=Event()
RELEASE=Event()


def blocked(inputs,settings,context):
    ENTERED.set()
    assert RELEASE.wait(3)
    return {'value':inputs['value']}


def echo(inputs,settings,context): return {'value':inputs['value']}


def object_cell(inputs,settings,context): return {'value':inputs['value'].iat[0,0][0]}


def task(name='echo',value=1,*,task_id='work',resources=None):
    command=BoundCommand('command.test.'+name,MethodRef(__name__+':'+name),None,
        {'value':PortContract('value')},{'value':PortContract('value')},
        resources=resources or {'cpu':1},reuse=ReuseContract(shareable=False,completed=False))
    return CommandTask(task_id,command,{'value':value})


def plan(*tasks):
    return PreparedPlan('test.admission',tasks,(),{'value':ValueRef(tasks[-1].task_id)},'plan','build')


@pytest.fixture(autouse=True)
def gates():
    ENTERED.clear();RELEASE.clear()
    yield
    RELEASE.set()


def test_graph_count_limit_precedes_snapshot_and_journal(monkeypatch):
    import stratbox.core.execution.service as module
    oversized=plan(*(task(task_id='node'+str(index)) for index in range(6)))
    with ExecutionService(settings=ExecutionSettings(max_plan_nodes=5)) as service:
        monkeypatch.setattr(module,'snapshot_plan',lambda _:pytest.fail('An oversized plan was copied'))
        with pytest.raises(ExecutionFailure,match='admission.plan_nodes'):service.submit(oversized)
        assert not service._runs and not service.journal.read()
        assert service._plan_bytes==service._plan_nodes==service._admitting==0


def test_literal_byte_limit_precedes_retention_and_journal():
    with ExecutionService(settings=ExecutionSettings(max_plan_bytes=10000)) as service:
        with pytest.raises(ExecutionFailure,match='admission.plan_bytes'):service.submit(plan(task(value=b'x'*20000)))
        assert not service._runs and not service.journal.read()


@pytest.mark.parametrize('factory',(lambda data:memoryview(data),lambda data:bytearray(data)))
def test_buffer_storage_cannot_hide_behind_a_small_view(factory):
    with ExecutionService(settings=ExecutionSettings(max_plan_bytes=10000)) as service:
        with pytest.raises(ExecutionFailure,match='admission.plan_bytes'):
            service.submit(plan(task(value=factory(b'x'*20000))))
        assert not service.journal.read()


def test_slot_payload_storage_is_included_before_copy():
    class Carrier:
        __slots__=('buffer',)
        def __init__(self,data):self.buffer=data
    with ExecutionService(settings=ExecutionSettings(max_plan_bytes=10000)) as service:
        with pytest.raises(ExecutionFailure,match='admission.plan_bytes'):
            service.submit(plan(task(value=Carrier(b'x'*20000))))
        assert not service.journal.read()


def test_nested_templates_count_even_before_any_dynamic_expansion():
    nested=plan(*(task(task_id='nested'+str(index)) for index in range(8)))
    mapped=MapTask('map',nested,(1,),item_output='value')
    with ExecutionService(settings=ExecutionSettings(max_plan_nodes=5)) as service:
        with pytest.raises(ExecutionFailure,match='admission.plan_nodes'):service.submit(plan(mapped))
        assert not service.journal.read()


def test_pending_limit_rejects_atomically_then_releases():
    with ExecutionService(settings=ExecutionSettings(active_runs=1,max_pending_runs=1)) as service:
        running=service.submit(plan(task('blocked')))
        assert ENTERED.wait(1)
        queued=service.submit(plan(task(value=2)))
        before=service.journal.read()
        with pytest.raises(ExecutionFailure,match='admission.pending_runs'):service.submit(plan(task(value=3)))
        assert service.journal.read()==before
        RELEASE.set()
        assert running.result(2).outcome==queued.result(2).outcome=='succeeded'


def test_aggregate_plan_bytes_include_queued_literals():
    settings=ExecutionSettings(active_runs=1,max_pending_runs=20,max_admitted_plan_bytes=24000)
    with ExecutionService(settings=settings) as service:
        running=service.submit(plan(task('blocked')))
        assert ENTERED.wait(1)
        handles=[]
        for index in range(20):
            before=service.journal.read()
            try:handles.append(service.submit(plan(task(value=b'x'*8000))))
            except ExecutionFailure as error:
                assert error.code=='admission.total_plan_bytes'
                assert service.journal.read()==before
                break
        else:pytest.fail('Queued payloads were not bounded')
        assert handles and service._plan_bytes<=24000
        RELEASE.set()
        running.result(2).close()
        for handle in handles:handle.result(2).close()
        assert service._plan_bytes==service._plan_nodes==0


def test_completed_open_results_also_bound_service_owners():
    with ExecutionService(settings=ExecutionSettings(max_open_runs=2)) as service:
        first=service.run(plan(task(value=1)));second=service.run(plan(task(value=2)))
        before=service.journal.read()
        with pytest.raises(ExecutionFailure,match='admission.open_runs'):service.submit(plan(task(value=3)))
        assert service.journal.read()==before
        first.close()
        assert service.run(plan(task(value=3))).output()==3
        second.close()


def test_queued_scientific_payload_is_detached_including_object_cells():
    frame=pd.DataFrame({'data':pd.Series([[7]],dtype=object)})
    queued_plan=plan(task('object_cell',frame))
    with ExecutionService(settings=ExecutionSettings(active_runs=1)) as service:
        running=service.submit(plan(task('blocked')))
        assert ENTERED.wait(1)
        queued=service.submit(queued_plan)
        queued_plan.tasks[0].inputs['value'].iat[0,0][0]=999
        RELEASE.set()
        assert running.result(2).outcome=='succeeded'
        assert queued.result(2).output()==7


def test_dynamic_slice_limit_inserts_no_partial_children():
    template=plan(task(value=TemplateInput('item'),task_id='first'),task(value=1,task_id='second'))
    mapped=MapTask('map',template,(1,),item_output='value')
    with ExecutionService(settings=ExecutionSettings(max_plan_nodes=6)) as service:
        handle=service.submit(plan(mapped));result=handle.result(2)
        assert result.outcome=='failed'
        assert any('admission.plan_nodes' in item for item in result.diagnostics)
        assert tuple(handle.snapshot()['tasks'])==('map',)


def test_close_during_snapshot_never_publishes_partial_admission(monkeypatch):
    import stratbox.core.execution.service as module
    started,release=Event(),Event()
    original=module.snapshot_plan
    def delayed(value):
        started.set();assert release.wait(2)
        return original(value)
    with ExecutionService(settings=ExecutionSettings(max_pending_runs=1)) as service,ThreadPoolExecutor(1) as pool:
        monkeypatch.setattr(module,'snapshot_plan',delayed)
        pending=pool.submit(service.submit,plan(task()))
        assert started.wait(1)
        with pytest.raises(ExecutionFailure,match='admission.pending_runs'):service.submit(plan(task()))
        service.close(wait=False)
        assert service.wait_closed(1)
        release.set()
        with pytest.raises(ExecutionFailure,match='service_closed'):pending.result(2)
        assert not service.journal.read() and not service._runs
        assert service._plan_bytes==service._plan_nodes==service._admitting==0
