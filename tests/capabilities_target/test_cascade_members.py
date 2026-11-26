"""Frozen cascade membership distinguishes required and optional unit outcomes."""
from stratbox.capabilities.catalog import standard_catalog
from stratbox.capabilities.model import CommandDefinition, OperationDefinition, ScenarioDefinition, PortContract, MethodRef, GraphBody, Call, InputRef, OutputRef
from stratbox.capabilities.preparation import prepare
from stratbox.core.execution.service import ExecutionService

INT=PortContract('integer',int)


def unit(inputs,settings,context):
    if inputs['value']<0: raise ValueError('unit.rejected')
    return {'value':inputs['value']}


def catalog():
    command=CommandDefinition('command.test.unit',inputs={'value':INT},outputs={'value':INT},method=MethodRef(__name__+':unit'))
    operation=OperationDefinition('operation.test.unit',inputs={'value':INT},outputs={'value':INT},
        body=GraphBody((Call('work',command.id,{'value':InputRef('value')}),),{'value':OutputRef('work')}))
    scenario=ScenarioDefinition('scenario.test.unit',inputs={'value':INT},outputs={'dataset':INT},
        body=GraphBody((Call('work',operation.id,{'value':InputRef('value')}),),{'dataset':OutputRef('work')}))
    return standard_catalog().with_definitions(command,operation,scenario)


def member(value,required=True):
    return {'capability_id':'scenario.test.unit','inputs':{'value':value},'required':required}


def test_optional_member_failure_is_excluded_and_recorded_without_blocking_required_success():
    plan=prepare('cascade.sources.refresh',inputs={'members':(member(2),member(-1,False))},catalog=catalog())
    assert not next(task for task in plan.tasks if task.task_id.endswith('member1/work/work')).required
    with ExecutionService() as service:
        result=service.run(plan,timeout=3)
        assert result.outcome=='succeeded',result.diagnostics
        assert result.output('results')==(2,)
        assert result.output('outcomes')==((0,'succeeded'),(1,'failed'))


def test_all_optional_failures_do_not_produce_an_empty_success_by_default():
    plan=prepare('cascade.sources.refresh',inputs={'members':(member(-1,False),)},catalog=catalog())
    with ExecutionService() as service:
        result=service.run(plan,timeout=3)
        assert result.outcome=='failed'


def test_required_member_failure_remains_a_cascade_failure():
    plan=prepare('cascade.sources.refresh',inputs={'members':(member(2),member(-1))},catalog=catalog())
    with ExecutionService() as service:
        result=service.run(plan,timeout=3)
        assert result.outcome=='failed'
