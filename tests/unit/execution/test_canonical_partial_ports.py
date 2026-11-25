"""Outcome-specific ports preserve partial data and unknown-effect evidence."""
from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    AcceptanceContract, CommandDefinition, OperationDefinition, GraphBody, Call,
    OutputRef, PortContract,
)
from stratbox.core.execution.runner import Completion
from stratbox.shared.data.processing import DataContract
from stratbox.sdk import StrategyBox


def partial_work(request, invocation):
    return Completion({'data': 7}, 'partial', 'fixture.partial')


def unknown_work(request, invocation):
    return Completion({'data': 7, 'preview': 'prepared'}, 'unknown', 'fixture.unknown')


def catalog(implementation):
    data = PortContract(DataContract('partial.data'), int, outcomes=frozenset({'succeeded', 'partial'}))
    preview = PortContract(DataContract('partial.preview'), str, required=False)
    command = CommandDefinition('partial.produce', __name__ + ':' + implementation,
        outputs={'data': data, 'preview': preview},
        acceptance=AcceptanceContract(partial_allowed=True))
    operation = OperationDefinition('partial.extract', GraphBody((Call('work', command.id),),
        {'data': OutputRef('work', 'data'), 'preview': OutputRef('work', 'preview')}),
        outputs=command.outputs, acceptance=AcceptanceContract(partial_allowed=True))
    return CatalogSnapshot(definitions=(command, operation))


def test_missing_success_only_port_does_not_destroy_qualified_partial_data():
    with StrategyBox(capabilities=catalog('partial_work')) as box:
        result = box.invoke('partial.extract', timeout=5)
        assert result.outcome == 'partial', result.diagnostics
        assert result.output('data') == 7
        assert 'preview' not in result.outputs
        physical = next(iter(result.results.values()))
        assert physical.outcome == 'partial'
        assert physical.value.data == 7 and physical.value.preview is None


def test_unknown_result_retains_prepared_value_without_successful_output_claim():
    with StrategyBox(capabilities=catalog('unknown_work')) as box:
        result = box.invoke('partial.extract', timeout=5)
        assert result.outcome == 'unknown', result.diagnostics
        assert not result.outputs
        physical = next(iter(result.results.values()))
        assert physical.value.data == 7 and physical.value.preview == 'prepared'
        assert all(d.code != 'acceptance.coherent_outputs_missing' for d in physical.diagnostics)
