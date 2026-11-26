"""Authored controls stay bounded and parameter dependencies are real edges."""
from dataclasses import replace

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.model import (
    Call, CollectCall, CommandDefinition, DispatchCall, GraphBody, InputRef,
    MapCall, MethodRef, OperationDefinition, OutputRef, PortContract, RepeatUntil,
)
from stratbox.capabilities.plan.models import (
    CollectTask, CommandTask, DispatchTask, MapTask, PreparedPlan, RepeatTask,
)
from stratbox.capabilities.preparation import prepare
from stratbox.core.execution import ExecutionService

INT = PortContract('integer', int)


def echo(inputs, settings, context):
    return {'value': inputs['value']}


def add_parameter(inputs, settings, context):
    return {'value': inputs['value'] + context.parameters['offset']}


def leaf(name, method='echo'):
    return CommandDefinition(name, inputs={'value': INT}, outputs={'value': INT},
        method=MethodRef(__name__ + ':' + method))


def test_parameters_pull_in_producer_and_prune_its_unread_outputs():
    source, add = leaf('command.test.source'), leaf('command.test.add', 'add_parameter')
    unavailable = CommandDefinition('command.test.backend', inputs={'value': INT},
        outputs={'value': INT}, specification_required=True)
    child = OperationDefinition('operation.test.source', inputs={'value': INT},
        outputs={'value': INT, 'extra': INT}, body=GraphBody((
            Call('main', source.id, {'value': InputRef('value')}),
            Call('backend', unavailable.id, {'value': InputRef('value')}),
        ), {'value': OutputRef('main'), 'extra': OutputRef('backend')}))
    operation = OperationDefinition('operation.test.parameters', outputs={'value': INT},
        body=GraphBody((
            # Author order deliberately differs from dependency order.
            Call('consume', add.id, {'value': 10}, parameters={'offset': OutputRef('producer')}),
            Call('producer', child.id, {'value': 7}),
        ), {'value': OutputRef('consume')}))
    definitions = (source, add, unavailable, child, operation)
    plan = prepare(operation.id, catalog=Catalog({d.id: d for d in definitions}))
    assert [task.command.id for task in plan.tasks] == [source.id, add.id]
    assert plan.tasks[0].task_id in plan.tasks[1].deps
    with ExecutionService() as service, service.run(plan) as result:
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output() == 17


def test_parameter_only_cycle_is_rejected_during_preparation():
    command = leaf('command.test.parameter', 'add_parameter')
    operation = OperationDefinition('operation.test.cycle', outputs={'value': INT},
        body=GraphBody((
            Call('a', command.id, {'value': 1}, parameters={'offset': OutputRef('b')}),
            Call('b', command.id, {'value': 1}, parameters={'offset': OutputRef('a')}),
        ), {'value': OutputRef('a')}))
    with pytest.raises(ValueError, match='graph.cycle'):
        prepare(operation.id, catalog=Catalog({d.id: d for d in (command, operation)}))


@pytest.mark.parametrize('value', [True, False, 1.5, '2', float('inf')])
def test_authored_and_physical_limits_require_exact_integers(value):
    for create in (
        lambda: MapCall('map', 'command.test', (), window=value),
        lambda: MapCall('map', 'command.test', (), max_items=value),
        lambda: RepeatUntil('repeat', GraphBody(()), None, max_passes=value),
        lambda: MapTask('map', None, (), window=value),
        lambda: MapTask('map', None, (), max_items=value),
        lambda: RepeatTask('repeat', None, None, max_passes=value),
    ):
        with pytest.raises(ValueError, match='invalid_'):
            create()


@pytest.mark.parametrize('name', ['window', 'max_items'])
@pytest.mark.parametrize('value', [True, 1.5, '2'])
def test_runtime_parameters_cannot_coerce_invalid_limits(name, value):
    command = leaf('command.test')
    operation = OperationDefinition('operation.test.map',
        outputs={'items': PortContract('items', tuple)}, body=GraphBody((
            MapCall('map', command.id, (1,), item_input='value', output_port='value'),
        ), {'items': OutputRef('map', 'items')}))
    with pytest.raises(ValueError, match='invalid_map_limits'):
        prepare(operation.id, parameters={name: value},
            catalog=Catalog({d.id: d for d in (command, operation)}))


def test_control_records_detach_mutable_collections():
    items, alternatives, dependencies = [{'value': [1]}], {'xlsx': 'operation.test'}, ['a']
    authored = MapCall('map', 'command.test', items)
    dispatch = DispatchCall('dispatch', {'format': ['xlsx']}, alternatives)
    mapped = MapTask('map', None, items, deps=dependencies)
    repeated = RepeatTask('repeat', None, items)
    collected = CollectTask('collect', tuple(items), item_guards={0: []})
    physical = DispatchTask('dispatch', None, alternatives)
    tasks = [mapped]
    plan = PreparedPlan('test', tasks, [], {}, 'test', 'build')
    items[0]['value'].append(2)
    alternatives['csv'] = 'operation.other'
    dependencies.append('b')
    tasks.clear()
    for value in (authored.items, mapped.items, repeated.initial, collected.items):
        assert value[0]['value'] == (1,)
    assert set(dispatch.alternatives) == set(physical.alternatives) == {'xlsx'}
    assert mapped.deps == ('a',) and plan.tasks == (mapped,)
    with pytest.raises(TypeError):
        collected.item_guards[1] = ()
