"""Each logical callable output has one accepted fact at its own scope."""
from collections import Counter

from stratbox.capabilities.catalog import standard_catalog
from stratbox.capabilities.model import OperationDefinition,GraphBody,Call,InputRef,OutputRef,PortContract
from stratbox.sdk import StrategyBox


def test_compiled_command_emits_one_output_fact_including_completed_reuse():
    with StrategyBox() as box:
        for _ in range(2):
            result=box.invoke('command.value.encode',inputs={'value':7})
            assert result.outcome=='succeeded',result.diagnostics
            accepted=[fact for fact in box.session.journal.read(run_id=result.run_id)
                if fact.kind=='output.accepted' and fact.scope_id=='root' and fact.output_name=='representation']
            assert len(accepted)==1
            assert accepted[0].command_id=='command.value.encode'


def test_nested_composite_outputs_keep_their_own_single_fact():
    inner=OperationDefinition('operation.test.inner',inputs={'value':PortContract('value')},
        outputs={'representation':PortContract('representation')},
        body=GraphBody((Call('encode','command.value.encode',{'value':InputRef('value')}),),
            {'representation':OutputRef('encode','representation')}))
    outer=OperationDefinition('operation.test.outer',inputs={'value':PortContract('value')},
        outputs={'representation':PortContract('representation')},
        body=GraphBody((Call('inner',inner.id,{'value':InputRef('value')}),),
            {'representation':OutputRef('inner','representation')}))
    with StrategyBox(catalog=standard_catalog().with_definitions(inner,outer)) as box:
        for _ in range(2):
            result=box.invoke(outer.id,inputs={'value':7})
            assert result.outcome=='succeeded',result.diagnostics
            accepted=[fact for fact in box.session.journal.read(run_id=result.run_id)
                if fact.kind=='output.accepted' and fact.output_name=='representation']
            counts=Counter(fact.scope_id for fact in accepted)
            assert counts=={'root/inner/encode':1,'root/inner':1,'root':1}
