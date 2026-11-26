"""Completion outcomes never manufacture acceptance or erase physical effects."""
from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.model import CommandDefinition, MethodRef, PortContract, AcceptanceContract
from stratbox.capabilities.preparation import prepare
from stratbox.core.execution.service import ExecutionService, CommandCompletion


def partial(inputs,settings,context):
    return CommandCompletion({'data':7},'partial',('source.partial',))


def unknown(inputs,settings,context):
    return CommandCompletion({'data':7},'unknown',('source.unknown',))


def rejected_after_write(inputs,settings,context):
    context.effect('storage.write','committed-before-rejection',lambda:'physically-stored')
    return {'data':'wrong-type'}


def definition(handler,*,effects=()):
    return CommandDefinition('command.test.'+handler,
        outputs={'data':PortContract('integer',int,outcomes=frozenset({'succeeded','partial'})),
                 'preview':PortContract('text',str,required=False)},
        method=MethodRef(__name__+':'+handler),effects=frozenset(effects),
        acceptance=AcceptanceContract(partial_allowed=True))


def test_partial_completion_retains_only_ports_that_admit_partial():
    command=definition('partial')
    with ExecutionService() as service:
        result=service.run(prepare(command.id,catalog=Catalog({command.id:command})),timeout=3)
        assert result.outcome=='partial',result.diagnostics
        assert result.output('data')==7 and 'preview' not in result.outputs


def test_unknown_completion_publishes_no_accepted_output_fact():
    command=definition('unknown')
    with ExecutionService() as service:
        result=service.run(prepare(command.id,catalog=Catalog({command.id:command})),timeout=3)
        assert result.outcome=='unknown' and not result.outputs
        assert not any(fact.kind=='output.accepted' for fact in service.journal.read(run_id=result.run_id))


def test_post_write_output_rejection_preserves_confirmed_effect_truth():
    command=definition('rejected_after_write',effects=('storage.write',))
    with ExecutionService() as service:
        result=service.run(prepare(command.id,catalog=Catalog({command.id:command})),timeout=3)
        assert result.outcome=='failed' and not result.outputs
        effect,=result.effects.values()
        assert effect.status=='confirmed' and effect.value=='physically-stored'
