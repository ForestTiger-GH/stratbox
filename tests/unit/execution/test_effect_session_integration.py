from dataclasses import dataclass
from threading import Event

from stratbox.composition import OperationStep, ScenarioDefinition, compile_workflow
from stratbox.core.execution import OperationDefinition, OperationSemantics, OutputPort, ProcessingStage, run
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.operations import OperationCatalog, OperationRef, operation_catalog
from stratbox.shared.data.processing import DataContract


@dataclass(frozen=True)
class Request:
    value: bytes = b'calculated'


DEFINITION = OperationDefinition('test.effect_session', 'commit', Request, bytes,
    possible_effects=frozenset({'storage.write'}),
    processing=OperationSemantics((ProcessingStage.PRESERVE,), summary='Commit one controlled test effect.',
        parameters=('value',), outputs=(OutputPort('value', DataContract('test.bytes')),)))

_STARTED = _RELEASE = None


def execute(request, *, context=None):
    def handler(value, invocation):
        for i in range(30):
            invocation.stage('step.' + str(i))
        def write():
            _STARTED.set()
            assert _RELEASE.wait(3)
            return EffectReceipt('storage.write', 'confirmed', effect_id='save')
        invocation.commit_effect('storage.write', 'save', write, resource='test.product')
        return value.value
    return run(DEFINITION, request, handler, context=context)


def test_cancelled_late_commit_retains_physical_evidence_with_saturated_progress():
    global _STARTED, _RELEASE
    _STARTED, _RELEASE = Event(), Event()
    base = operation_catalog()
    catalog = OperationCatalog((*base.references,
        OperationRef(DEFINITION.operation_id, __name__ + ':execute', definition=DEFINITION)), base.registrations)
    definition = ScenarioDefinition('commit', (OperationStep('save', DEFINITION.operation_id),))
    with ExecutionSession(catalog, settings=ExecutionSettings(max_workers=1, event_capacity=1)) as execution:
        handle = execution.submit(compile_workflow(definition, catalog))
        assert _STARTED.wait(2)
        assert handle.cancel()
        # Cancellation is a coordinator control event, independent of the
        # overfull diagnostic view. The live physical worker remains occupied.
        assert execution.ledger.snapshot().occupied['worker'] == 1
        _RELEASE.set()
        result = handle.result(3)
        assert result.outcome == 'cancelled'
        assert any(effect.effect_id == 'save' and effect.state == 'confirmed' for effect in result.effects)
        assert execution.ledger.snapshot().occupied.get('worker', 0) == 0
        record, = execution.effects.snapshot()
        assert record.receipt.state == 'confirmed'
        assert record.current is False
        assert execution.journal.health_snapshot().evicted > 0
        assert execution.journal.source.pending == 1
