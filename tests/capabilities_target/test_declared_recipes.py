"""A capability declares its pure graph recipe without a compiler ID dispatcher."""
from dataclasses import replace

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.commands.standard import C
from stratbox.capabilities.model import CommandDefinition, GraphBody, InputRef, MethodRef, OperationDefinition, OutputRef, PortContract, Call
from stratbox.sdk import StrategyBox

NUMBER=PortContract("test.number",int)


def increment(inputs,settings,context):
    context.checkpoint()
    return {"value":inputs["value"]+1}


def choose_repeated_increment(definition,values,parameters,record,catalog):
    count=parameters.get("count",1)
    if type(count) is not int or not 1<=count<=4:
        raise ValueError("extension.invalid_count")
    steps=[];value=InputRef("value")
    for ordinal in range(count):
        name="increment"+str(ordinal)
        steps.append(Call(name,"command.extension.increment",{"value":value}))
        value=OutputRef(name,"value")
    return replace(definition,body=GraphBody(tuple(steps),{"value":value}))


def changes_identity(definition,*args):
    return replace(definition,id="operation.wrong_identity")


def test_external_operation_recipe_executes_for_unregistered_standard_id():
    command=CommandDefinition("command.extension.increment",inputs={"value":NUMBER},outputs={"value":NUMBER},
        method=MethodRef(__name__+":increment"))
    # Neither the standard operation catalog nor a preparation switch knows this ID.
    operation=OperationDefinition("operation.extension.increment_history",inputs={"value":NUMBER},outputs={"value":NUMBER},
        recipe=MethodRef(__name__+":choose_repeated_increment"))
    with StrategyBox(catalog=Catalog({command.id:command,operation.id:operation}),domains=DomainCatalog({})) as box:
        plan=box.prepare(operation.id,inputs={"value":7},parameters={"count":3})
        assert len(plan.tasks)==3
        assert {task.command.method.locator for task in plan.tasks}=={__name__+":increment"}
        result=box.run(plan)
        assert result.outcome=="succeeded" and result.output("value")==10


def test_declared_recipe_cannot_silently_replace_the_callable_identity():
    operation=OperationDefinition("operation.extension.fixed_identity",inputs={},outputs={},
        recipe=MethodRef(__name__+":changes_identity"))
    with StrategyBox(catalog=Catalog({operation.id:operation}),domains=DomainCatalog({})) as box:
        with pytest.raises(ValueError,match="recipe.definition_identity_changed"):
            box.prepare(operation.id)


def test_technical_command_reuse_follows_explicit_declaration_instead_of_its_id():
    command=C("command.extension.read_mutable_inventory",{}, {},
        handler=__name__+":increment",observes_mutable_state=True)
    assert not command.reuse.inflight_eligible and not command.reuse.completed_eligible
    assert command.method.locator==__name__+":increment"
