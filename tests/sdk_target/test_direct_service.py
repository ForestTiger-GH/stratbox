"""SDK and graph calls use one execution path with accepted named results."""
import pytest
from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model import (
    CommandDefinition, OperationDefinition, ScenarioDefinition, CascadeDefinition,
    PortContract, MethodRef, GraphBody, Call, InputRef, OutputRef, Condition,
)
from stratbox.sdk import StrategyBox

NUMBER=PortContract('test.number',int)


def add(inputs,settings,context):
    context.checkpoint()
    return {'value':inputs['left']+inputs['right']}


def broken(inputs,settings,context):
    return {'wrong':1}


def command(method='add'):
    return CommandDefinition('command.test.add',inputs={'left':NUMBER,'right':NUMBER},outputs={'value':NUMBER},
        method=MethodRef(__name__+':'+method),resources={'cpu':1})


def operation():
    return OperationDefinition('operation.test.add',inputs={'left':NUMBER,'right':NUMBER},outputs={'value':NUMBER},
        body=GraphBody((Call('add','command.test.add',{'left':InputRef('left'),'right':InputRef('right')}),),
                       {'value':OutputRef('add','value')}))


def test_direct_command_and_operation_have_equal_values_and_separate_scopes():
    cmd,op=command(),operation()
    with StrategyBox(catalog=Catalog({cmd.id:cmd,op.id:op}),domains=DomainCatalog({})) as box:
        direct=box.invoke(cmd.id,inputs={'left':5,'right':7})
        composed=box.invoke(op.id,inputs={'left':5,'right':7})
        assert direct.outcome==composed.outcome=='succeeded'
        assert direct.output()==composed.output()==12
        assert direct.run_id!=composed.run_id
        assert composed.scopes
        direct.close();composed.close()


def test_temporary_root_definition_uses_prepared_plan_and_same_service():
    cmd,op=command(),operation()
    with StrategyBox(catalog=Catalog({cmd.id:cmd}),domains=DomainCatalog({})) as box:
        plan=box.prepare(op,inputs={'left':3,'right':4})
        result=box.submit(plan).result(timeout=5)
        assert result.outcome=='succeeded' and result.output()==7
        with pytest.raises(ValueError,match='prepared_plan_arguments'):
            box.submit(plan,inputs={})


def test_missing_named_output_cannot_become_accepted_success():
    cmd=command('broken')
    with StrategyBox(catalog=Catalog({cmd.id:cmd}),domains=DomainCatalog({})) as box:
        result=box.invoke(cmd.id,inputs={'left':1,'right':2})
        assert result.outcome!='succeeded'
        assert 'value' not in result.outputs


def test_closed_client_rejects_new_work():
    cmd=command()
    box=StrategyBox(catalog=Catalog({cmd.id:cmd}),domains=DomainCatalog({}))
    box.close()
    with pytest.raises(RuntimeError,match='sdk.closed'):
        box.invoke(cmd.id,inputs={'left':1,'right':2})
