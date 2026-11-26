"""Actual ownership, acceptance and bounded consumers in the current service."""
from dataclasses import dataclass, replace
import gc
from threading import Event
import weakref

import numpy as np
import pandas as pd
import pytest

from stratbox.capabilities.model import AcceptanceContract, MethodRef, PortContract, ReuseContract, SemanticPredicate
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution.service import ExecutionService, ExecutionSettings, ExecutionFailure

ENTERED=Event()
RELEASE=Event()
CONSUMED=[]
PRODUCED=[]
NO_REUSE=ReuseContract(shareable=False,completed=False)


def command(name, inputs=None, outputs=None, *, reuse=NO_REUSE, acceptance=None):
    return BoundCommand('command.test.'+name,MethodRef(__name__+':'+name),None,
        inputs or {},outputs or {'value':PortContract('value')},resources={'cpu':1},reuse=reuse,
        acceptance=acceptance or AcceptanceContract())


def plan(tasks, outputs=None):
    return PreparedPlan('test.values',tuple(tasks),(),outputs or {'value':ValueRef(tasks[-1].task_id)},'values','build')


def produce_pair(inputs,settings,context):
    return {'left':7,'right':-1}


def consume(inputs,settings,context):
    CONSUMED.append(inputs['value'])
    return {'value':inputs['value']}


def echo(inputs,settings,context):
    return {'value':inputs['value']}


def blob(inputs,settings,context):
    return {'value':b'x'*inputs['size']}


def native_frame(inputs,settings,context):
    return {'value':pd.DataFrame({'amount':[1,2]})}


def native_array(inputs,settings,context):
    value=np.arange(inputs.get('size',4),dtype=np.float64)
    PRODUCED.append(weakref.ref(value))
    return {'value':value}


def edit_array(inputs,settings,context):
    inputs['value'][0]=999
    return {'value':int(inputs['value'][0])}


def first_array(inputs,settings,context):
    return {'value':int(inputs['value'][0])}


def sum_array(inputs,settings,context):
    return {'value':len(inputs['value'])}


def wait_number(inputs,settings,context):
    ENTERED.set()
    if not RELEASE.wait(5): raise ValueError('test.wait_timeout')
    return {'value':inputs['value']}


def aliases(inputs,settings,context):
    return {'value':inputs['left'] is inputs['right']}


@dataclass(frozen=True)
class FieldValue:
    actual:int

    @property
    def unsafe(self):
        CONSUMED.append('property evaluated')
        raise ValueError('test.property_was_evaluated')


def fields_value(inputs,settings,context):
    return {'value':FieldValue(7)}


def test_rejected_named_output_group_never_exposes_an_individually_valid_member():
    CONSUMED.clear()
    outputs={'left':PortContract('number',int),
        'right':PortContract('nonnegative',int,predicates=(SemanticPredicate('', 'minimum',0),))}
    work=command('produce_pair',outputs=outputs,acceptance=AcceptanceContract(coherent_outputs=('left','right')))
    consumer=command('consume',inputs={'value':PortContract('number',int)},outputs={'value':PortContract('number',int)})
    with ExecutionService() as service:
        result=service.run(plan((CommandTask('pair',work,{}),
            CommandTask('consume',consumer,{'value':ValueRef('pair','left')},('pair',)))))
        assert result.outcome=='failed'
        assert not result.outputs and not CONSUMED
        assert not any(fact.kind=='output.accepted' and fact.task_id=='pair'
                       for fact in service.journal.read(run_id=result.run_id))
        result.close()
        assert service._retained_bytes==0


def test_native_array_consumers_are_isolated_from_the_same_producer():
    source=command('native_array',outputs={'value':PortContract('array',np.ndarray)})
    edit=command('edit_array',inputs={'value':PortContract('array',np.ndarray)},outputs={'value':PortContract('number',int)})
    inspect=command('first_array',inputs={'value':PortContract('array',np.ndarray)},outputs={'value':PortContract('number',int)})
    tasks=(CommandTask('source',source,{}),CommandTask('edit',edit,{'value':ValueRef('source')},('source',)),
        CommandTask('inspect',inspect,{'value':ValueRef('source')},('source','edit')))
    with ExecutionService() as service:
        result=service.run(plan(tasks,{'edited':ValueRef('edit'),'original':ValueRef('inspect')}))
        assert result.outcome=='succeeded',result.diagnostics
        assert result.output('edited')==999
        assert result.output('original')==0


def test_each_public_read_is_isolated_from_another_reader_of_accepted_frame():
    with ExecutionService() as service:
        result=service.run(plan((CommandTask('frame',command('native_frame',outputs={'value':PortContract('frame',pd.DataFrame)}),{}),)))
        assert result.outcome=='succeeded',result.diagnostics
        first=result.output()
        first.loc[0,'amount']=999
        assert result.output().loc[0,'amount']==1
        from_mapping=result.outputs['value']
        from_mapping.loc[0,'amount']=777
        assert result.output().loc[0,'amount']==1


def test_shared_completed_work_gives_independent_native_results():
    work=command('native_frame',outputs={'value':PortContract('frame',pd.DataFrame)},reuse=ReuseContract())
    with ExecutionService() as service:
        left=service.run(plan((CommandTask('frame',work,{}),)))
        right=service.run(plan((CommandTask('frame',work,{}),)))
        assert left.outcome==right.outcome=='succeeded'
        first_read=left.output()
        first_read.loc[0,'amount']=999
        assert right.output().loc[0,'amount']==1
        assert any(fact.kind=='work.reused' for fact in service.journal.read(run_id=right.run_id))


def test_aliased_scientific_inputs_have_one_physical_copy_per_consumer():
    frame=pd.DataFrame({'value':range(100)})
    work=command('aliases',inputs={'left':PortContract('frame',pd.DataFrame),'right':PortContract('frame',pd.DataFrame)},
                 outputs={'value':PortContract('bool',bool)})
    with ExecutionService() as service:
        result=service.run(plan((CommandTask('alias',work,{'left':frame,'right':frame}),)))
        assert result.outcome=='succeeded',result.diagnostics
        assert result.output() is True


def test_result_ownership_keeps_capacity_after_service_close_then_releases_once():
    service=ExecutionService()
    result=service.run(plan((CommandTask('blob',command('blob',inputs={'size':PortContract('size',int)},outputs={'value':PortContract('bytes',bytes)}),{'size':1024}),)))
    assert result.outcome=='succeeded'
    charged=service._retained_bytes
    assert charged>=1024
    service.close()
    assert result.output()==b'x'*1024 and service._retained_bytes==charged
    result.close()
    assert service._retained_bytes==0
    result.close()
    assert service._retained_bytes==0
    with pytest.raises(ExecutionFailure,match='result_closed'):result.output()


def test_live_result_capacity_cannot_be_reused_before_the_actual_owner_closes():
    settings=ExecutionSettings(max_workers=1,max_retained_bytes=2048)
    task=CommandTask('blob',command('blob',inputs={'size':PortContract('size',int)},outputs={'value':PortContract('bytes',bytes)}),{'size':1024})
    with ExecutionService(settings=settings) as service:
        first=service.run(plan((task,)))
        assert first.outcome=='succeeded',first.diagnostics
        charged=service._retained_bytes
        second=service.run(plan((task,)))
        assert second.outcome=='failed' and not second.outputs
        second.close()
        assert service._retained_bytes==charged
        first.close()
        assert service._retained_bytes==0
        third=service.run(plan((task,)))
        assert third.outcome=='succeeded',third.diagnostics
        third.close()
        assert service._retained_bytes==0


def test_unprojected_intermediate_is_released_after_its_last_consumer_before_run_end():
    ENTERED.clear();RELEASE.clear();PRODUCED.clear()
    size=256*1024
    source=command('native_array',inputs={'size':PortContract('size',int)},outputs={'value':PortContract('array',np.ndarray)})
    summary=command('sum_array',inputs={'value':PortContract('array',np.ndarray)},outputs={'value':PortContract('number',int)})
    gate=command('wait_number',inputs={'value':PortContract('number',int)},outputs={'value':PortContract('number',int)})
    tasks=(CommandTask('source',source,{'size':size}),
        CommandTask('summary',summary,{'value':ValueRef('source')},('source',)),
        CommandTask('gate',gate,{'value':ValueRef('summary')},('summary',)))
    with ExecutionService(settings=ExecutionSettings(max_workers=1,max_retained_bytes=16*size*8)) as service:
        handle=service.submit(plan(tasks))
        try:
            assert ENTERED.wait(3)
            gc.collect()
            assert PRODUCED and PRODUCED[0]() is None
            with service._condition:assert service._resident_size()<size*8
        finally:
            RELEASE.set()
        result=handle.result(3)
        assert result.outcome=='succeeded' and result.output()==size


def test_value_projection_uses_declared_fields_without_evaluating_properties():
    CONSUMED.clear()
    source=command('fields_value',outputs={'value':PortContract('field_value',FieldValue)})
    consumer=command('consume',inputs={'value':PortContract('number',int)},outputs={'value':PortContract('number',int)})
    with ExecutionService() as service:
        good=service.run(plan((CommandTask('source',source,{}),
            CommandTask('read',consumer,{'value':ValueRef('source',path='actual')},('source',)))))
        assert good.outcome=='succeeded' and good.output()==7
        CONSUMED.clear()
        bad=service.run(plan((CommandTask('source',source,{}),
            CommandTask('read',consumer,{'value':ValueRef('source',path='unsafe')},('source',)))))
        assert bad.outcome=='failed' and not bad.outputs
        assert any('field_projection_required' in code for code in bad.diagnostics)
        assert CONSUMED==[]


def test_closed_runs_keep_provenance_metadata_bounded_and_live_result_pinned():
    settings=ExecutionSettings(max_accepted_values=4)
    work=command('echo',inputs={'value':PortContract('integer',int)},outputs={'value':PortContract('integer',int)})
    with ExecutionService(settings=settings) as service:
        live=service.run(plan((CommandTask('live',work,{'value':-1}),)))
        from stratbox.shared.data.values import fingerprint
        pinned=fingerprint(-1)
        for number in range(30):
            current=service.run(plan((CommandTask('value',work,{'value':number}),)))
            assert current.outcome=='succeeded',current.diagnostics
            current.close()
            assert len(service._accepted)<=4 and pinned in service._accepted
        assert live.output()==-1
        live.close()
