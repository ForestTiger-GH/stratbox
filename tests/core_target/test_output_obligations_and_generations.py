"""Output use, recursive admission and physical generation boundaries."""
from dataclasses import replace
from math import isfinite, isinf
from threading import Event, Thread

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model import (
    Call, CollectCall, CommandDefinition, GraphBody, MethodRef,
    OperationDefinition, OutputRef, PortContract, ReuseContract,
)
from stratbox.capabilities.plan.models import (
    BoundCommand, CommandTask, MapTask, PreparedPlan, TemplateInput, ValueRef,
)
from stratbox.core.execution.service import CommandCompletion, ExecutionService, ExecutionFailure
from stratbox.sdk import StrategyBox


def echo(inputs, settings, context):
    return {'value': inputs['value']}


def remaining(inputs, settings, context):
    return {'value': context.remaining_seconds()}


def report_failure(inputs, settings, context):
    return CommandCompletion({'report': ('validation failed',)}, context.parameters['outcome'], ('fixture.invalid',))


def plan(tasks, outputs=None):
    return PreparedPlan('test', tuple(tasks), (), outputs or {'value': ValueRef(tasks[-1].task_id)}, 'test', 'test')


@pytest.mark.parametrize('outcome', ('failed', 'unknown'))
@pytest.mark.parametrize('completion', ('all_selected', 'eligible_subset', 'diagnostic'))
def test_diagnostic_payload_cannot_fulfil_an_analytical_member(outcome, completion):
    report = PortContract('report', tuple, role='diagnostic', outcomes=frozenset({'succeeded', 'failed', 'unknown'}))
    command = CommandDefinition('command.test.report', outputs={'report': report},
        method=MethodRef(__name__ + ':report_failure'), parameters={'outcome': outcome},
        reuse=ReuseContract(shareable=False, completed=False))
    operation = OperationDefinition('operation.test.collect', outputs={
        'items': PortContract('reports' if completion == 'diagnostic' else 'result_collection', tuple,
                              role='diagnostic' if completion == 'diagnostic' else 'data'),
        'outcomes': PortContract('unit_outcomes', tuple, role='diagnostic',
                                 outcomes=frozenset({'succeeded', 'partial', 'failed', 'unknown'}))},
        body=GraphBody((Call('work', command.id, required=False),
            CollectCall('collect', (OutputRef('work', 'report'),), min_items=1, completion=completion)),
            {'items': OutputRef('collect', 'items'), 'outcomes': OutputRef('collect', 'outcomes')}))
    with StrategyBox(catalog=Catalog({command.id: command, operation.id: operation}),
                     domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(operation.id) as result:
            statuses = result.output('outcomes')
            assert len(statuses) == 1 and statuses[0].outcome == outcome
            if completion == 'diagnostic':
                assert result.outcome == 'succeeded'
                assert result.output('items') == (('validation failed',),)
            else:
                assert result.outcome not in {'succeeded', 'partial'}
                assert 'items' not in result.outputs
        accepted = [fact for fact in box.session.journal.read() if fact.kind == 'output.accepted']
        assert not any(fact.output_name == 'report' and fact.data.get('output_role') != 'diagnostic' for fact in accepted)


def test_completed_open_result_does_not_extend_a_new_generation_deadline():
    command = BoundCommand('command.test.remaining', MethodRef(__name__ + ':remaining'), {}, {},
        {'value': PortContract('seconds', float)}, reuse=ReuseContract(shareable=True, completed=False))
    prepared = plan((CommandTask('work', command, {}),))
    with ExecutionService() as service:
        first = service.run(prepared)
        try:
            assert isinf(first.output())
            with service.run(prepared, timeout=5) as second:
                assert isfinite(second.output()) and 0 < second.output() <= 5
        finally:
            first.close()


@pytest.mark.parametrize('implied', (False, True))
def test_nested_cycles_are_rejected_before_admission_or_effects(implied):
    command = BoundCommand('command.test.echo', MethodRef(__name__ + ':echo'), {},
        {'value': PortContract('value')}, {'value': PortContract('value')})
    cyclic = plan((
        CommandTask('a', command, {'value': ValueRef('b') if implied else TemplateInput('item')}, () if implied else ('b',)),
        CommandTask('b', command, {'value': ValueRef('a') if implied else TemplateInput('item')}, () if implied else ('a',)),
    ))
    mapped = plan((MapTask('map', cyclic, (1,), item_output='value'),), {'value': ValueRef('map', 'items')})
    with ExecutionService() as service:
        with pytest.raises(ExecutionFailure, match='plan.cycle'):
            service.submit(mapped)
        assert service.active_physical_count == 0 and service.quiescent
        assert not service.journal.read()
        # A bad request is local to its admission; a later valid call still runs.
        with service.run(plan((CommandTask('ok', command, {'value': 7}),))) as result:
            assert result.outcome == 'succeeded' and result.output() == 7


def test_nested_template_captures_rebind_without_merging_local_namespaces():
    command = BoundCommand('command.test.echo', MethodRef(__name__ + ':echo'), {},
        {'value': PortContract('value')}, {'value': PortContract('value')})
    inner = plan((CommandTask('consumer', command, {'value': ValueRef('captured')}),))
    member = plan((CommandTask('captured', command, {'value': TemplateInput('item')}),
        MapTask('inner', inner, (1,), item_input='other', item_output='value')), {'value': ValueRef('inner', 'items')})
    prepared = plan((MapTask('outer', member, (7, 8), item_output='value'),), {'value': ValueRef('outer', 'items')})
    with ExecutionService() as service:
        with service.run(prepared) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert result.output() == ((7,), (8,))


STARTED = Event()
RELEASE = Event()


def wait_for_release(inputs, settings, context):
    STARTED.set()
    assert RELEASE.wait(5)
    return {'value': 7}


def test_admission_pause_waits_for_physical_settlement_and_then_resumes():
    STARTED.clear(); RELEASE.clear()
    command = BoundCommand('command.test.wait', MethodRef(__name__ + ':wait_for_release'), {}, {},
        {'value': PortContract('value', int)}, reuse=ReuseContract(shareable=False, completed=False))
    prepared = plan((CommandTask('work', command, {}),))
    paused, unblock_pause = Event(), Event()
    errors = []
    with ExecutionService() as service:
        handle = service.submit(prepared)
        assert STARTED.wait(2)

        def pause():
            try:
                with service.admission_pause(timeout=5):
                    paused.set()
                    assert unblock_pause.wait(5)
            except BaseException as error:
                errors.append(error)

        thread = Thread(target=pause)
        thread.start()
        try:
            assert not paused.wait(.05)
            RELEASE.set()
            with handle.result(timeout=5) as result:
                assert result.outcome == 'succeeded'
            assert paused.wait(2)
            assert service.active_physical_count == 0 and service.quiescent
            with pytest.raises(ExecutionFailure, match='execution.admission_paused'):
                service.submit(prepared)
        finally:
            RELEASE.set(); unblock_pause.set()
            thread.join(5)
        assert not thread.is_alive() and not errors
        with service.run(prepared, timeout=5) as result:
            assert result.outcome == 'succeeded'
