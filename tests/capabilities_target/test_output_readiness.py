"""Composite output promises gate consumers before their commands execute."""
from threading import Event
import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.model import (
    PortContract, MethodRef, CommandDefinition, OperationDefinition,
    GraphBody, Call, InputRef, OutputRef, AcceptanceContract, SemanticPredicate,
)
from stratbox.capabilities.preparation import prepare
from stratbox.core.execution.service import ExecutionService, ExecutionSettings

CONSUMED=Event()
RELEASE=Event()
STARTED=Event()
CALLS=[]
INT=PortContract('integer',int)


def echo(inputs, settings, context):
    return {'value':inputs['value']}


def wait_bad(inputs, settings, context):
    STARTED.set()
    assert RELEASE.wait(3), 'test.release_timeout'
    return {'value':-1}


def consume(inputs, settings, context):
    CALLS.append(inputs['value'])
    CONSUMED.set()
    return {'value':inputs['value']}


def reject_check(inputs, settings, context):
    raise ValueError('check.rejected')


def command(name, handler):
    return CommandDefinition('command.test.'+name, inputs={'value':INT},outputs={'value':INT},
        method=MethodRef(__name__+':'+handler))


def graph(*, coherent=False, wait=False, check=False):
    good=command('echo','echo'); bad=command('bad','wait_bad' if wait else 'echo')
    consumer=command('consume','consume'); validator=command('check','reject_check')
    steps=[Call('good',good.id,{'value':InputRef('value')}),Call('bad',bad.id,{'value':-1})]
    if check: steps.append(Call('check',validator.id,{'value':OutputRef('good')}))
    child=OperationDefinition('operation.test.child',inputs={'value':INT},
        outputs={'good':INT,'bad':INT},
        acceptance=AcceptanceContract(coherent_outputs=('good','bad') if coherent else (),
            predicates=(SemanticPredicate('bad','minimum',0,'bad.negative'),)),
        body=GraphBody(tuple(steps),{'good':OutputRef('good'),'bad':OutputRef('bad')},
            required_checks=('check',) if check else ()))
    parent=OperationDefinition('operation.test.parent',inputs={'value':INT},outputs={'value':INT},
        body=GraphBody((Call('child',child.id,{'value':InputRef('value')}),
            Call('consume',consumer.id,{'value':OutputRef('child','good' if wait or check else 'bad')})),
            {'value':OutputRef('consume')}))
    return parent,Catalog({d.id:d for d in (good,bad,consumer,validator,child,parent)})


@pytest.fixture(autouse=True)
def clear_events():
    CONSUMED.clear();RELEASE.clear();STARTED.clear();CALLS.clear()
    yield
    RELEASE.set()


def test_rejected_composite_output_never_reaches_outer_consumer():
    definition,catalog=graph()
    plan=prepare(definition.id,inputs={'value':2},catalog=catalog)
    with ExecutionService() as service:
        result=service.run(plan,timeout=4)
    assert result.outcome=='failed' and not CALLS
    assert any('bad.negative' in item for item in result.diagnostics)


def test_independent_output_can_be_consumed_while_unrelated_output_is_pending():
    definition,catalog=graph(wait=True)
    plan=prepare(definition.id,inputs={'value':2},catalog=catalog)
    with ExecutionService(settings=ExecutionSettings(max_workers=2)) as service:
        handle=service.submit(plan,timeout=4)
        assert STARTED.wait(2)
        assert CONSUMED.wait(2), 'independent accepted output was unnecessarily blocked'
        assert not handle.done()
        RELEASE.set()
        result=handle.result(3)
    assert CALLS==[2]
    assert result.scopes['root/child']=='failed'


def test_coherent_outputs_wait_together_and_reject_together():
    definition,catalog=graph(wait=True,coherent=True)
    plan=prepare(definition.id,inputs={'value':2},catalog=catalog)
    assert {task.task_id for task in plan.tasks}>={'root/child/good','root/child/bad'}
    with ExecutionService(settings=ExecutionSettings(max_workers=2)) as service:
        handle=service.submit(plan,timeout=4)
        assert STARTED.wait(2)
        assert not CONSUMED.wait(.05)
        RELEASE.set()
        result=handle.result(3)
    assert result.outcome=='failed' and not CALLS


def test_required_scope_check_gates_exported_output():
    definition,catalog=graph(check=True)
    plan=prepare(definition.id,inputs={'value':2},catalog=catalog)
    with ExecutionService() as service:
        result=service.run(plan,timeout=4)
    assert result.outcome=='failed' and not CALLS


def test_global_predicate_waits_for_all_named_outputs_before_releasing_any():
    definition,catalog=graph(wait=True)
    child=catalog.get('operation.test.child')
    from dataclasses import replace
    child=replace(child,acceptance=AcceptanceContract(predicates=(SemanticPredicate('', 'equals', {'good':2}),)))
    catalog=Catalog({**dict(catalog.definitions),child.id:child})
    plan=prepare(definition.id,inputs={'value':2},catalog=catalog)
    with ExecutionService(settings=ExecutionSettings(max_workers=2)) as service:
        handle=service.submit(plan,timeout=4)
        assert STARTED.wait(2)
        assert not CONSUMED.wait(.05)
        RELEASE.set()
        result=handle.result(3)
    assert result.outcome=='failed' and not CALLS


def test_empty_passthrough_scope_respects_external_prerequisite_before_acceptance():
    bad=command('wait','wait_bad'); consumer=command('consume','consume')
    passthrough=OperationDefinition('operation.test.forward',inputs={'value':INT},outputs={'value':INT},
        body=GraphBody((),{'value':InputRef('value')}))
    root=OperationDefinition('operation.test.root',outputs={'value':INT},body=GraphBody((
        Call('prerequisite',bad.id,{'value':0}),
        Call('forward',passthrough.id,{'value':7},depends_on=('prerequisite',)),
        Call('consume',consumer.id,{'value':OutputRef('forward')})),{'value':OutputRef('consume')}))
    plan=prepare(root.id,catalog=Catalog({d.id:d for d in (bad,consumer,passthrough,root)}))
    with ExecutionService(settings=ExecutionSettings(max_workers=2)) as service:
        handle=service.submit(plan,timeout=4)
        assert STARTED.wait(2)
        assert not CONSUMED.wait(.05)
        RELEASE.set()
        result=handle.result(3)
    assert result.outcome=='succeeded' and CALLS==[7]


def test_false_condition_on_empty_passthrough_never_publishes_output():
    from stratbox.capabilities.model import Condition
    consumer=command('consume','consume')
    forward=OperationDefinition('operation.test.forward',outputs={'value':INT},
        body=GraphBody((),{'value':7}))
    root=OperationDefinition('operation.test.root',outputs={'value':INT},body=GraphBody((
        Call('forward',forward.id,condition=Condition(False)),
        Call('consume',consumer.id,{'value':OutputRef('forward')})),{'value':OutputRef('consume')}))
    with ExecutionService() as service:
        result=service.run(prepare(root.id,catalog=Catalog({d.id:d for d in (consumer,forward,root)})),timeout=3)
        assert result.outcome=='failed' and not CALLS
        assert not any(fact.kind=='output.accepted' and fact.scope_id=='root/forward'
            for fact in service.journal.read(run_id=result.run_id))
