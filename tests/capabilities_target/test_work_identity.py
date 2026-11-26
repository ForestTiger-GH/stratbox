"""Reuse follows actual content, interpretation, method and observation policy."""
from dataclasses import replace
from threading import Event
import pytest

from stratbox.capabilities.catalog import Catalog, DomainCatalog
from stratbox.capabilities.model import CommandDefinition, PortContract, MethodRef, ReuseContract, DomainSpec, CalculationSpec
from stratbox.capabilities.preparation import prepare
from stratbox.capabilities.model.immutable import fingerprint
from stratbox.core.execution.service import ExecutionService, ExecutionSettings
from stratbox.shared.data.values import EncodedProduct, SourceDataset
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.identity import ByteIdentity

CALLS=[]
ENTERED=Event()
RELEASE=Event()


def observe(inputs,settings,context):
    CALLS.append(inputs['value'])
    return {'value':inputs['value']}


def blocked(inputs,settings,context):
    CALLS.append(inputs['value'])
    ENTERED.set()
    assert RELEASE.wait(3)
    return {'value':inputs['value']}


def definition(handler='observe',reuse=None):
    return CommandDefinition('command.test.observe',inputs={'value':PortContract('value')},
        outputs={'value':PortContract('value')},method=MethodRef(__name__+':'+handler),reuse=reuse or ReuseContract())


def test_completed_false_still_joins_inflight_work_then_reexecutes_after_completion():
    CALLS.clear();ENTERED.clear();RELEASE.clear()
    command=definition('blocked',ReuseContract(completed=False))
    catalog=Catalog({command.id:command})
    plan=prepare(command.id,inputs={'value':3},catalog=catalog)
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        first=service.submit(plan,timeout=4)
        assert ENTERED.wait(2)
        second=service.submit(plan,timeout=4)
        # Inspect admission under the coordinator lock before releasing producer.
        from time import monotonic
        deadline=monotonic()+2
        while not second.snapshot()['tasks']['root']=='waiting_shared' and monotonic()<deadline:
            Event().wait(.002)
        assert second.snapshot()['tasks']['root']=='waiting_shared'
        RELEASE.set()
        assert first.result(3).output()==second.result(3).output()==3
        assert len(CALLS)==1
        assert service.run(plan,timeout=3).output()==3
        assert len(CALLS)==2


def test_equal_bytes_with_distinct_media_or_semantic_descriptors_do_not_share():
    CALLS.clear()
    command=definition();catalog=Catalog({command.id:command})
    values=(EncodedProduct(b'1','application/json',descriptor={'schema':'number'}),
            EncodedProduct(b'1','text/csv',descriptor={'schema':'cell'}))
    with ExecutionService() as service:
        for value in values:
            assert service.run(prepare(command.id,inputs={'value':value},catalog=catalog),timeout=3).outcome=='succeeded'
    assert len(CALLS)==2


def test_exact_qualified_source_uses_remain_consumer_significant():
    CALLS.clear()
    command=definition();catalog=Catalog({command.id:command})
    def value(issue,group):
        use=SourceUse(SourceCoordinate('A','family',group,issue,material_identity=ByteIdentity.of(b'same')),
            'operand','domain_validated')
        return SourceDataset('A',({'value':1},),source_uses=(use,))
    with ExecutionService() as service:
        for supplied in (value('2026-10-01','first'),value('2026-11-01','second')):
            assert service.run(prepare(command.id,inputs={'value':supplied},catalog=catalog),timeout=3).outcome=='succeeded'
    assert len(CALLS)==2


def test_prepared_identity_binds_actual_settings_order_multiplicity_and_code_basis():
    command=definition();catalog=Catalog({command.id:command})
    first=prepare(command.id,inputs={'value':(1,2,1)},catalog=catalog,build_identity='build-A')
    reordered=prepare(command.id,inputs={'value':(1,1,2)},catalog=catalog,build_identity='build-A')
    other_build=prepare(command.id,inputs={'value':(1,2,1)},catalog=catalog,build_identity='build-B')
    domains=DomainCatalog({'test':DomainSpec('test',{}, {},calculations={'test.calc':CalculationSpec('test.calc',{},settings={'factor':2})})})
    specified=prepare(command.id,inputs={'value':(1,2,1)},catalog=catalog,domains=domains,target='test.calc',build_identity='build-A')
    other_method=replace(command,method=MethodRef(__name__+':blocked'))
    changed=prepare(command.id,inputs={'value':(1,2,1)},catalog=Catalog({command.id:other_method}),build_identity='build-A')
    assert len({plan.fingerprint for plan in (first,reordered,other_build,specified,changed)})==5


def test_prepared_dataframe_owns_its_values_and_identity_handles_typed_cells():
    pd=pytest.importorskip('pandas')
    frame=pd.DataFrame({'value':[1,2]})
    command=definition();plan=prepare(command.id,inputs={'value':frame},catalog=Catalog({command.id:command}))
    before=fingerprint(plan.tasks[0].inputs['value'])
    frame.loc[0,'value']=100
    assert plan.tasks[0].inputs['value'].loc[0,'value']==1
    assert fingerprint(plan.tasks[0].inputs['value'])==before


def scientific_helper(value,factor=2):
    return value*factor


def scientific(inputs,settings,context):
    return {'value':scientific_helper(inputs['value'])}


def test_actual_reachable_helper_defaults_change_execution_reuse(monkeypatch):
    command=replace(definition(),method=MethodRef(__name__+':scientific'))
    catalog=Catalog({command.id:command})
    plan=prepare(command.id,inputs={'value':3},catalog=catalog,build_identity='fixed-build')
    with ExecutionService() as service:
        assert service.run(plan,timeout=3).output()==6
        monkeypatch.setattr(scientific_helper,'__defaults__',(3,))
        assert service.run(plan,timeout=3).output()==9


def test_missing_explicit_method_fails_one_invocation_and_keeps_service_usable():
    command=definition()
    missing=replace(command,method=MethodRef(__name__+':missing_explicit_algorithm'))
    with ExecutionService() as service:
        rejected=service.run(prepare(missing.id,inputs={'value':3},catalog=Catalog({missing.id:missing})),timeout=3)
        assert rejected.outcome=='failed'
        accepted=service.run(prepare(command.id,inputs={'value':3},catalog=Catalog({command.id:command})),timeout=3)
        assert accepted.outcome=='succeeded' and accepted.output()==3
