"""Every selected member remains reviewable across failure and cancellation."""
from threading import Event

import pytest

from stratbox.capabilities.catalog import standard_catalog
from stratbox.capabilities.model import (CommandDefinition, OperationDefinition, MethodRef,
    PortContract, ReuseContract, AcceptanceContract, Call, CollectCall, GraphBody, OutputRef)
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, MapTask, PreparedPlan, TemplateInput, ValueRef
from stratbox.capabilities.preparation import prepare
from stratbox.core.execution.service import CommandCompletion, ExecutionService, ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.values import Material, ImmutableMaterialRef


INT = PortContract('integer', int)
TUPLE = PortContract('result_collection', tuple)
NO_REUSE = ReuseContract(deterministic=False, shareable=False, completed=False)
ENTERED, RELEASE = Event(), Event()
CALLS = []


def unit(inputs, settings, context):
    value = inputs['value']
    CALLS.append(value)
    if value == 9:
        ENTERED.set()
        while not RELEASE.wait(.002):
            context.checkpoint()
    if value == -2:
        def lost_acknowledgement():
            raise ConnectionError('fixture acknowledgement lost')
        context.effect('storage.write', 'member-unknown-effect', lost_acknowledgement)
        # A later local failure must not hide the uncertain external effect.
        raise ValueError('fixture.after_unknown_effect')
    if value == -3:
        return CommandCompletion({'value': value}, outcome='partial', findings=('fixture.partial_input_scope',))
    if value < 0:
        raise ValueError('fixture.member_rejected')
    return {'value': value}


@pytest.fixture(autouse=True)
def reset_probe():
    ENTERED.clear(); RELEASE.clear(); CALLS.clear()
    yield
    RELEASE.set()


def collect_plan(values, *, optional=()):
    command = CommandDefinition('command.test.member', inputs={'value': INT}, outputs={'value': INT},
        method=MethodRef(__name__ + ':unit'), effects=frozenset({'storage.write'}), reuse=NO_REUSE)
    steps = tuple(Call('member' + str(index), command.id, {'value': value}, required=index not in optional)
                  for index, value in enumerate(values))
    collection = CollectCall('collect', tuple(OutputRef('member' + str(index), 'value') for index in range(len(values))),
                             optional_items=frozenset(optional), min_items=1)
    operation = OperationDefinition('operation.test.collect', outputs={'values': TUPLE, 'outcomes': PortContract('unit_outcomes', tuple)},
        body=GraphBody((*steps, collection), {'values': OutputRef('collect', 'items'), 'outcomes': OutputRef('collect', 'outcomes')}))
    return prepare(operation.id, catalog=standard_catalog().with_definitions(command, operation))


def mapped(values, *, completion='all_selected', retain=False):
    inputs = {'value': INT, **({'reference': PortContract('artifact', ImmutableMaterialRef)} if retain else {})}
    command = BoundCommand('command.test.member', MethodRef(__name__ + ':unit'), {}, inputs,
        {'value': PortContract('integer', int, outcomes=frozenset({'succeeded', 'partial'}))},
        effects=frozenset({'storage.write'}), reuse=NO_REUSE, acceptance=AcceptanceContract(partial_allowed=True))
    tasks = []
    if retain:
        commit = BoundCommand('command.artifact.commit', MethodRef('stratbox.core.commands.artifacts:artifact_commit'), {},
            {'material': PortContract('material', Material), 'destination': PortContract('destination', str)},
            {'reference': PortContract('artifact', ImmutableMaterialRef), 'receipt': PortContract('receipt')},
            effects=frozenset({'storage.write'}), required_providers=frozenset({'filestore'}))
        tasks.append(CommandTask('save', commit, {'material': Material(b'original'), 'destination': 'originals'}))
    tasks.append(CommandTask('work', command, {'value': TemplateInput('item'),
        **({'reference': ValueRef('save', 'reference')} if retain else {})}, deps=('save',) if retain else ()))
    template = PreparedPlan('operation.test.member', tuple(tasks), (), {'value': ValueRef('work', 'value')}, 'template', 'test')
    task = MapTask('map', template, tuple(values), item_output='value', window=1, completion=completion, scope_id='batch')
    return PreparedPlan('operation.test.map', (task,), (), {'values': ValueRef('map', 'items'),
        'outcomes': ValueRef('map', 'outcomes')}, 'mapped', 'test')


@pytest.mark.parametrize('values,expected,effect_state', [((1, -1, 2), 'failed', None), ((1, -2, 2), 'unknown', 'unknown')])
def test_collect_reports_every_required_member_including_failure_and_unknown(values, expected, effect_state):
    with ExecutionService() as service:
        with service.run(collect_plan(values), timeout=3) as result:
            assert result.outcome == expected, result.diagnostics
            assert result.output('values') == (1, 2)
            outcomes = result.output('outcomes')
            assert len(outcomes) == 3 and [item.ordinal for item in outcomes] == [0, 1, 2]
            assert [item.outcome for item in outcomes] == ['succeeded', expected, 'succeeded']
            assert outcomes[1].effect_state == effect_state
            assert len({item.member_key for item in outcomes}) == 3


def test_collect_optional_failure_preserves_success_and_full_outcomes():
    with ExecutionService() as service:
        with service.run(collect_plan((1, -1, 2), optional=(1,)), timeout=3) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert len(result.output('outcomes')) == 3


def test_map_keeps_an_explicitly_admitted_partial_result_qualified():
    with ExecutionService() as service:
        with service.run(mapped((1, -3)), timeout=3) as result:
            assert result.outcome == 'partial'
            assert result.output('values') == (1, -3)
            assert [item.outcome for item in result.output('outcomes')] == ['succeeded', 'partial']


@pytest.mark.parametrize('completion,expected', [('all_selected', 'failed'), ('eligible_subset', 'succeeded')])
def test_map_preserves_retained_earlier_stage_when_a_member_later_fails(tmp_path, completion, expected):
    with ExecutionService(providers={'filestore': LocalFileStore(str(tmp_path))}) as service:
        with service.run(mapped((1, -1), completion=completion, retain=True), timeout=3) as result:
            assert result.outcome == expected, result.diagnostics
            assert result.output('values') == (1,)
            outcomes = result.output('outcomes')
            assert [item.outcome for item in outcomes] == ['succeeded', 'failed']
            assert 'retained' in outcomes[1].available_stages
            assert outcomes[1].references and outcomes[1].effect_state == 'confirmed'


@pytest.mark.parametrize('scope', [None, 'batch'])
def test_cancelled_map_reports_unstarted_members_without_expanding_them(scope):
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        handle = service.submit(mapped((1, 9, 3)))
        assert ENTERED.wait(2)
        assert handle.cancel(scope)
        with handle.result(3) as result:
            assert result.outcome == ('cancelled' if scope is None else 'failed')
            assert CALLS == [1, 9]
            assert result.output('values') == (1,)
            outcomes = result.output('outcomes')
            assert [item.ordinal for item in outcomes] == [0, 1, 2]
            assert [item.outcome for item in outcomes] == ['succeeded', 'cancelled', 'cancelled']
