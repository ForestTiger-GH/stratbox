"""Effect truth, provider admission and budget failures survive command errors."""
from dataclasses import replace
from threading import Event

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model import CommandDefinition, MethodRef, PortContract, ReuseContract
from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.limits import BudgetMeter, ExecutionBudget, BudgetClockError, BudgetExceeded
from stratbox.sdk import StrategyBox

CALLS=[]
ENTERED=Event()
RELEASE=Event()


@pytest.fixture(autouse=True)
def reset():
    CALLS.clear();ENTERED.clear();RELEASE.clear()
    yield
    RELEASE.set()


def effect_then_return(inputs,settings,context):
    for index in range(context.parameters.get('count',1)):
        def action(index=index):
            CALLS.append(index)
            return 'stored'
        context.effect('storage.write',f'effect-{index}',action,resource=f'file-{index}')
    if context.parameters.get('raise'):raise ValueError('failure after physical acknowledgement')
    return {'value':inputs['value']}


def uncertain_after_wait(inputs,settings,context):
    def action():
        CALLS.append('started');ENTERED.set()
        assert RELEASE.wait(3)
        raise OSError('physical outcome cannot be observed')
    context.effect('storage.write','uncertain',action,resource='file')
    return {'value':1}


def provider_probe(inputs,settings,context):
    CALLS.append('handler')
    return {'value':context.provider('selected').value}


def direct(method,*,parameters=None,effects=('storage.write',),providers=()):
    return CommandDefinition('command.test.obligations',inputs={'value':PortContract('value')},
        outputs={'value':PortContract('value')},method=MethodRef(__name__+':'+method),
        parameters=parameters or {},effects=frozenset(effects),required_providers=frozenset(providers),
        reuse=ReuseContract(shareable=False))


def box(command,**kwargs):
    return StrategyBox(catalog=Catalog({command.id:command}),domains=DomainCatalog({}),**kwargs)


def test_confirmed_effect_survives_later_handler_error_and_result_close():
    command=direct('effect_then_return',parameters={'raise':True})
    with box(command) as client:
        result=client.invoke(command.id,inputs={'value':1})
        assert result.outcome=='failed' and not result.outputs
        receipt=result.effects['effect-0']
        assert receipt.status=='confirmed' and CALLS==[0]
        result.close()
        assert client.session.lookup_effect(receipt.effect_id).status=='confirmed'


def test_undeclared_effect_fails_before_physical_action():
    command=direct('effect_then_return',effects=())
    with box(command) as client:
        result=client.invoke(command.id,inputs={'value':1})
        assert result.outcome=='failed' and not CALLS
        assert not result.effects


def test_effect_capacity_is_reserved_before_each_distinct_mutation():
    command=direct('effect_then_return',parameters={'count':2})
    with box(command,settings=ExecutionSettings(effect_capacity=1)) as client:
        result=client.invoke(command.id,inputs={'value':1})
        assert result.outcome=='failed' and CALLS==[0]
        assert result.effects['effect-0'].status=='confirmed'
        assert tuple(result.effects)==('effect-0',)
        assert any('capacity' in str(item) for item in result.diagnostics)


@pytest.mark.parametrize('kind,resource',(('notification.deliver','file-0'),('storage.write','another-file')))
def test_rejected_foreign_unknown_effect_does_not_contaminate_this_run(tmp_path,kind,resource):
    from stratbox.core.execution.effect_state import FileEffectState
    from stratbox.core.execution.service import EffectReceipt
    state=FileEffectState(tmp_path/'effects')
    original=EffectReceipt('effect-0',kind,'unknown',resource=resource)
    original, claimed = state.begin(original)
    assert claimed
    command=direct('effect_then_return')
    with box(command,providers={'effect_state':state}) as client:
        result=client.invoke(command.id,inputs={'value':1})
        assert result.outcome=='failed' and not CALLS
        assert not result.effects and not result.effect_ids
        assert 'effect.identity_conflict' in result.diagnostics
        assert state.get('effect-0')==original


def test_output_budget_failure_preserves_confirmed_effect():
    command=direct('effect_then_return')
    settings=ExecutionSettings(run_limits=ExecutionBudget(output_bytes=0))
    with box(command,settings=settings) as client:
        result=client.invoke(command.id,inputs={'value':b'large output'})
        assert result.outcome=='failed' and not result.outputs
        assert result.effects['effect-0'].status=='confirmed' and CALLS==[0]


def test_cancellation_does_not_hide_uncertain_physical_outcome():
    command=direct('uncertain_after_wait')
    with box(command) as client:
        handle=client.submit(command.id,inputs={'value':1})
        try:
            assert ENTERED.wait(2)
            assert handle.cancel()
        finally:RELEASE.set()
        result=handle.result(4)
        assert result.effects['uncertain'].status=='unknown'
        assert result.outcome=='unknown'
        assert CALLS==['started']


def test_explicit_provider_bindings_are_per_service_and_not_cached_globally():
    class Provider:
        def __init__(self,value):self.value=value
    command=direct('provider_probe',effects=(),providers=('selected',))
    with box(command,providers={'selected':Provider('A')}) as first,box(command,providers={'selected':Provider('B')}) as second:
        assert first.invoke(command.id,inputs={'value':1}).output()=='A'
        assert second.invoke(command.id,inputs={'value':1}).output()=='B'


@pytest.mark.parametrize('providers',({}, {'selected':None}))
def test_unavailable_explicit_provider_never_runs_handler(providers):
    command=direct('provider_probe',effects=(),providers=('selected',))
    with box(command,providers=providers) as client:
        result=client.invoke(command.id,inputs={'value':1})
        assert result.outcome=='failed' and not CALLS


@pytest.mark.parametrize('ticks',((2.,1.),(2.,float('nan')),(2.,float('inf'))))
def test_strict_clock_failure_never_becomes_success(ticks):
    values=iter(ticks)
    meter=BudgetMeter(ExecutionBudget(seconds=10),now=lambda:next(values))
    with pytest.raises(BudgetClockError):meter.checkpoint()


def test_equal_clock_is_valid_and_elapsed_budget_expires():
    values=iter((2.,2.,2.5,3.))
    meter=BudgetMeter(ExecutionBudget(seconds=1),now=lambda:next(values))
    meter.checkpoint();meter.checkpoint()
    with pytest.raises(BudgetExceeded):meter.checkpoint()


def test_unlimited_budget_does_not_read_optional_clock():
    def broken():raise RuntimeError('no clock available')
    meter=BudgetMeter(ExecutionBudget(),now=broken)
    meter.checkpoint();meter.charge('objects',1)
    assert dict(meter.usage())['objects']==1


def secret_failure(inputs,settings,context):
    raise RuntimeError(inputs['value'])


@pytest.mark.parametrize('secret',('credential=NEVER_SERIALIZE','private.api.token'))
def test_unexpected_exception_text_is_not_exported_as_public_execution_evidence(secret):
    command=direct('secret_failure',effects=())
    with box(command) as client:
        result=client.invoke(command.id,inputs={'value':secret})
        facts=client.session.journal.read(run_id=result.run_id)
        assert result.outcome=='failed'
        assert secret not in repr((result.diagnostics,facts))
        assert result.diagnostics


def test_optional_observer_failure_preserves_work_and_accepted_result():
    called=Event()
    def broken(fact):
        called.set()
        raise OSError('sink unavailable')
    command=direct('effect_then_return',effects=())
    # No side effect is attempted in this fixture.
    command=replace(command,parameters={'count':0})
    with box(command,observer=broken) as client:
        result=client.invoke(command.id,inputs={'value':12})
        assert result.outcome=='succeeded' and result.output()==12
        assert called.wait(2)
        from time import monotonic,sleep
        until=monotonic()+2
        while not client.session.observer_status().failed and monotonic()<until:sleep(.001)
        health=client.session.observer_status()
        assert health.failed and any('optional_sink' in item.code for item in health.diagnostics)
        assert health.replay_after


@pytest.mark.parametrize('settings',({'max_workers':float('nan')},{'active_runs':True},{'max_retained_bytes':float('inf')}))
def test_nonfinite_or_boolean_capacity_cannot_create_a_stuck_execution_queue(settings):
    with pytest.raises(ValueError,match='invalid_settings'):ExecutionSettings(**settings)


def test_nonfinite_deadline_is_rejected_before_run_admission():
    command=direct('effect_then_return',effects=(),parameters={'count':0})
    with box(command) as client:
        with pytest.raises(ValueError,match='invalid_timeout'):
            client.submit(command.id,inputs={'value':1},timeout=float('nan'))
        assert not client.session._runs and not CALLS


def confirmed_after_wait(inputs,settings,context):
    def action():
        ENTERED.set()
        assert RELEASE.wait(3)
        CALLS.append('committed')
        return 'stored'
    context.effect('storage.write','slow-commit',action,resource='file')
    return {'value':1}


def test_journal_exhaustion_during_mutation_returns_addressable_effect_truth():
    from stratbox.core.observability.journal import MemoryJournal
    journal=MemoryJournal(capacity=10)
    command=direct('confirmed_after_wait')
    with box(command,journal=journal) as client:
        handle=client.submit(command.id,inputs={'value':1})
        try:
            assert ENTERED.wait(2)
            while True:
                try:journal.append(kind='pressure',run_id='external')
                except RuntimeError:break
        finally:RELEASE.set()
        result=handle.result(4)
        assert result.outcome!='succeeded'
        assert result.effects['slow-commit'].status=='confirmed'
        assert CALLS==['committed']
        assert all(value==0 for value in client.session._used.values())
        assert any('journal' in str(item) for item in result.diagnostics)
