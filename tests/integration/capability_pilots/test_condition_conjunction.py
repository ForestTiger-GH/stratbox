"""A disabled outer scope suppresses nested guarded effects and expansion."""
import pytest

from stratbox.capabilities.model import (
    CommandDefinition,OperationDefinition,ScenarioDefinition,GraphBody,Call,
    MapCall,CollectCall,Condition,InputRef,OutputRef,ParameterRef,PortContract,ReuseContract,
)
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract

FLAG = PortContract(DataContract("audit.flag"),bool)
FLAGS = PortContract(DataContract("audit.flags"),tuple,collection=True)


def flag(request,invocation):
    return request["flag"]


def capture(request,invocation):
    invocation.provider("audit_recorder").append(True)
    invocation.effect(EffectReceipt("storage.write","confirmed",effect_id="captured"))
    return True


def definitions(parent_enabled,mode):
    flag_command = CommandDefinition("audit.flag",__name__+":flag",parameters={"flag":True},outputs={"value":FLAG})
    flag_operation = OperationDefinition("audit.flag_operation",GraphBody((
        Call("leaf","audit.flag",parameters={"flag":ParameterRef("flag")}),
    ),{"value":OutputRef("leaf")}),parameters={"flag":True},outputs={"value":FLAG})
    capture_command = CommandDefinition("audit.capture",__name__+":capture",outputs={"value":FLAG},
        required_capabilities=frozenset({"audit_recorder"}),effects=frozenset({"storage.write"}),
        reuse=ReuseContract(shareable=False,effects=frozenset({"storage.write"})))
    capture_operation = OperationDefinition("audit.save",GraphBody((Call("leaf","audit.capture"),),{"value":OutputRef("leaf")}),
        outputs={"value":FLAG},effects=frozenset({"storage.write"}))
    item = ScenarioDefinition("audit.item",GraphBody((Call("save","audit.save"),),{"value":OutputRef("save")}),
        inputs={"item":FLAG},outputs={"value":FLAG})
    gates = (
        Call("local","audit.flag_operation",parameters={"flag":False}),
        Call("probe","audit.flag_operation",condition=Condition("local",equals=True)),
    )
    if mode == "map":
        tail = (MapCall("effect","audit.item",(True,False,True),window=1,
                       condition=Condition("probe",statuses=("skipped",))),)
        contract = PortContract(FLAG.schema,object,collection=True)
    elif mode == "collect":
        tail = (
            CollectCall("collected",(OutputRef("local"),),FLAGS,FLAG,
                        condition=Condition("probe",statuses=("skipped",))),
            Call("effect","audit.save",condition=Condition("collected",statuses=("succeeded",))),
        )
        contract = FLAG
    else:
        tail = (Call("effect","audit.save",condition=Condition("probe",statuses=("skipped",))),)
        contract = FLAG
    child = ScenarioDefinition("audit.effect_child",GraphBody((*gates,*tail),{"value":OutputRef("effect")}),outputs={"value":contract})
    optional = PortContract(contract.schema,contract.value_type,required=False,collection=contract.collection)
    parent = ScenarioDefinition("audit.effect_parent",GraphBody((
        Call("guard","audit.flag_operation",parameters={"flag":parent_enabled}),
        Call("child","audit.effect_child",condition=Condition("guard",equals=True),required=False),
    ),{"guard":OutputRef("guard"),"saved":OutputRef("child")}),outputs={"guard":FLAG,"saved":optional})
    return CatalogSnapshot((flag_command,flag_operation,capture_command,capture_operation,item,child,parent))


@pytest.mark.parametrize("mode,expected",[("call",1),("map",3),("collect",1)])
@pytest.mark.parametrize("enabled",[False,True])
def test_outer_and_inner_guards_control_effects(enabled,mode,expected):
    recorded = []
    snapshot = definitions(enabled,mode)
    with StrategyBox(capabilities=snapshot,providers={"audit_recorder":recorded},
                     settings=ExecutionSettings(max_workers=1,map_window=1)) as box:
        plan = box.prepare("audit.effect_parent")
        result = box.submit(plan).result(10)
        assert len(recorded) == (expected if enabled else 0),(result.diagnostics,result.tasks)
        assert result.output("guard") is enabled
        if not enabled:
            assert "saved" not in result.outputs
        else:
            assert result.outcome == "succeeded",(result.diagnostics,result.scopes,[(task.task_id,task.state,task.reason) for task in result.tasks])
        result.close()
