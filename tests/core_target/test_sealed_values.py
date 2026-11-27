"""Private payload identity, bounded copying and control-path independence."""
from array import array
from dataclasses import dataclass
from threading import current_thread

import pandas as pd
import numpy as np
import pytest

from stratbox.capabilities.catalog import Catalog, DomainCatalog
from stratbox.capabilities.model import (Call, CommandDefinition, GraphBody,
    InputRef, MethodRef, OperationDefinition, OutputRef, PortContract, ReuseContract)
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, CollectTask, PreparedPlan, ValueRef
from stratbox.core.execution import ExecutionService
from stratbox.core.execution.owned_values import _isolate
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import SourceDataset, fingerprint


def echo(inputs, settings, context):
    return {'value': inputs['value']}


def mutate(inputs, settings, context):
    inputs['value'].native.iat[0, 0][0]['value'] = 99
    return {'value': inputs['value']}


def command(handler='echo'):
    return CommandDefinition('command.test.sealed', inputs={'value': PortContract('value')},
        outputs={'value': PortContract('value')}, method=MethodRef(__name__ + ':' + handler),
        reuse=ReuseContract(shareable=False, completed=False))


def dataset():
    return SourceDataset('source', ({'value': 7},), native=pd.DataFrame({
        'nested': pd.Series([[{'value': 7}]], dtype=object)}))


def test_mutable_working_input_and_result_reader_never_mutate_the_sealed_value():
    worker = command('mutate')
    operation = OperationDefinition('operation.test.sealed', inputs={'value': PortContract('value')},
        outputs={'original': PortContract('value'), 'changed': PortContract('value')},
        body=GraphBody((Call('change', worker.id, {'value': InputRef('value')}),),
            {'original': InputRef('value'), 'changed': OutputRef('change')}))
    source = dataset()
    with StrategyBox(catalog=Catalog({worker.id: worker, operation.id: operation}),
            domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(operation.id, inputs={'value': source}) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert result.output('original').native.iat[0, 0][0]['value'] == 7
            assert result.output('changed').native.iat[0, 0][0]['value'] == 99
            reader = result.output('original')
            reader.native.iat[0, 0][0]['value'] = 123
            assert result.output('original').native.iat[0, 0][0]['value'] == 7
        assert source.native.iat[0, 0][0]['value'] == 7
        assert box.session.value_statistics()['resident_bytes'] == 0


class MutableKey:
    def __init__(self, label): self.label = label
    def __hash__(self): return hash(self.label)
    def __eq__(self, other): return isinstance(other, MutableKey) and self.label == other.label


def test_mapping_keys_receive_private_owners():
    key = MutableKey('before')
    detached = _isolate({key: [1]}, max_bytes=4096)
    copied = next(iter(detached))
    assert copied is not key
    key.label = 'after'
    assert copied.label == 'before' and detached[copied] == [1]


def test_mutable_dataframe_axis_is_rejected_instead_of_shared():
    frame = pd.DataFrame({'value': [7]}, index=pd.Index([MutableKey('before')]))
    with pytest.raises(ValueError, match='axis_not_admitted'):
        _isolate(frame, max_bytes=4096)


class PretendFrame:
    def __init__(self): self.cells = [7]
    def memory_usage(self, **kwargs): return 8
    def copy(self, **kwargs): return self


def test_unknown_python_owner_cannot_bypass_copying_with_dataframe_methods():
    original = PretendFrame()
    private = _isolate(original, max_bytes=4096)
    private.cells[0] = 99
    assert original.cells == [7]


def test_numpy_scalars_are_admitted_without_admitting_mutable_void_scalars():
    for scalar in (np.float64(1.5), np.int32(7), np.datetime64('2026-01-01')):
        assert _isolate(scalar) is scalar
    mutable = np.array([(1,)], dtype=[('value', 'i4')])[0]
    with pytest.raises(ValueError, match='opaque_owner_not_admitted'):
        _isolate(mutable)


def test_unsupported_native_mutability_is_rejected_before_admission():
    bound = BoundCommand('command.test.native', MethodRef(__name__ + ':echo'), {},
        {'value': PortContract('value')}, {'value': PortContract('value')})
    bad = PreparedPlan('test', (CommandTask('work', bound, {'value': array('i', [1, 2])}),), (),
        {'value': ValueRef('work')}, 'test', 'test')
    good = PreparedPlan('test', (CommandTask('work', bound, {'value': 7}),), (),
        {'value': ValueRef('work')}, 'test', 'test')
    with ExecutionService() as service:
        with pytest.raises(ValueError, match='native_container_not_admitted'):
            service.submit(bad)
        assert service.value_statistics()['resident_bytes'] == 0
        with service.run(good) as result:
            assert result.output() == 7


@dataclass(frozen=True)
class UntrustedDigest:
    value: int
    fingerprint: str = 'caller-controlled'


def test_caller_digest_cannot_alias_distinct_content():
    assert fingerprint(UntrustedDigest(1)) != fingerprint(UntrustedDigest(2))


def test_coordinator_never_hashes_or_copies_scientific_payloads(monkeypatch):
    import stratbox.shared.data.value_identity as identities
    import stratbox.core.execution.owned_values as owned
    seen = []
    exact, isolate = identities.exact_fingerprint, owned._isolate
    def hashed(value, **kwargs):
        if isinstance(value, SourceDataset):
            seen.append(('hash', current_thread().name))
        return exact(value, **kwargs)
    def copied(value, *args, **kwargs):
        if isinstance(value, SourceDataset):
            seen.append(('copy', current_thread().name))
        return isolate(value, *args, **kwargs)
    monkeypatch.setattr(identities, 'exact_fingerprint', hashed)
    monkeypatch.setattr(owned, '_isolate', copied)
    worker = command()
    with StrategyBox(catalog=Catalog({worker.id: worker}), domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(worker.id, inputs={'value': dataset()}) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            before = box.session.value_statistics()['exact_identity_passes']
            for _ in range(50):
                box.session.status(result.run_id)
                box.session.value_statistics()
            assert box.session.value_statistics()['exact_identity_passes'] == before
    assert seen and not any(thread == 'stratbox-coordinator' for _, thread in seen)


def test_literal_collection_member_uses_its_sealed_identity(monkeypatch):
    import stratbox.shared.data.value_identity as identities
    seen = []
    original = identities.exact_fingerprint
    def hashed(value, **kwargs):
        if isinstance(value, SourceDataset): seen.append(current_thread().name)
        return original(value, **kwargs)
    monkeypatch.setattr(identities, 'exact_fingerprint', hashed)
    prepared = PreparedPlan('test', (CollectTask('collect', (dataset(),)),), (),
        {'value': ValueRef('collect', 'items')}, 'test', 'test')
    with ExecutionService() as service:
        with service.run(prepared) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert len(result.output()) == 1
    assert seen and 'stratbox-coordinator' not in seen
