"""Adversarial review of output origin and member completion boundaries."""
from threading import Event, Lock

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model import (
    Call, CollectCall, CommandDefinition, GraphBody, InputRef, MapCall,
    MethodRef, OperationDefinition, OutputRef, PortContract, ReuseContract,
)
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, MapTask, PreparedPlan, TemplateInput, ValueRef
from stratbox.core.execution.service import ExecutionService, ExecutionSettings
from stratbox.sdk import StrategyBox


NO_REUSE = ReuseContract(shareable=False, completed=False)
INT = PortContract('integer', int)
ALL_OUTCOMES = frozenset({'succeeded', 'partial', 'failed', 'unknown', 'cancelled'})


def reported_value(inputs, settings, context):
    from stratbox.core.execution.service import CommandCompletion
    return CommandCompletion({'value': inputs['item']}, context.parameters['outcome'], ('fixture.reported',))


def early_value(inputs, settings, context):
    return {'value': inputs['item']}


def late_completion(inputs, settings, context):
    if inputs['item'] < 0:
        raise ValueError('fixture.required_completion_failed')
    return {'value': inputs['item']}


def report_definitions(outcome, role):
    report = PortContract('integer', int, role=role, outcomes=ALL_OUTCOMES)
    command = CommandDefinition('command.test.origin_report', inputs={'item': INT}, outputs={'value': report},
        method=MethodRef(__name__ + ':reported_value'), parameters={'outcome': outcome}, reuse=NO_REUSE)
    wrapper = OperationDefinition('operation.test.origin_wrapper', inputs={'item': INT}, outputs={'value': report},
        body=GraphBody((Call('report', command.id, {'item': InputRef('item')}, required=False),),
                       {'value': OutputRef('report', 'value')}))
    return command, wrapper


@pytest.mark.parametrize('outcome', ('failed', 'unknown'))
@pytest.mark.parametrize('role', ('data', 'diagnostic'))
@pytest.mark.parametrize('completion', ('all_selected', 'eligible_subset'))
def test_map_cannot_promote_reported_origin_through_successful_optional_wrapper(outcome, role, completion):
    command, wrapper = report_definitions(outcome, role)
    mapped = OperationDefinition('operation.test.origin_map', outputs={
        'items': PortContract('result_collection', tuple),
        'outcomes': PortContract('unit_outcomes', tuple, role='diagnostic', outcomes=ALL_OUTCOMES)},
        body=GraphBody((MapCall('map', wrapper.id, (7,), output_port='value', completion=completion),),
                      {'items': OutputRef('map', 'items'), 'outcomes': OutputRef('map', 'outcomes')}))
    with StrategyBox(catalog=Catalog({item.id: item for item in (command, wrapper, mapped)}),
                     domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(mapped.id) as result:
            assert 'outcomes' in result.outputs, (result.outcome, result.diagnostics, result.outputs)
            outcomes = result.output('outcomes')
            assert len(outcomes) == 1
            assert outcomes[0].outcome == outcome
            assert result.outcome not in {'succeeded', 'partial'}
            assert 'items' not in result.outputs


@pytest.mark.parametrize('outcome', ('failed', 'unknown'))
def test_collect_cannot_promote_reported_origin_through_successful_optional_wrapper(outcome):
    command, wrapper = report_definitions(outcome, 'data')
    collected = OperationDefinition('operation.test.origin_collect', outputs={
        'items': PortContract('result_collection', tuple),
        'outcomes': PortContract('unit_outcomes', tuple, role='diagnostic', outcomes=ALL_OUTCOMES)},
        body=GraphBody((Call('wrapped', wrapper.id, {'item': 7}, required=False),
                       CollectCall('collect', (OutputRef('wrapped', 'value'),), min_items=1)),
                      {'items': OutputRef('collect', 'items'), 'outcomes': OutputRef('collect', 'outcomes')}))
    with StrategyBox(catalog=Catalog({item.id: item for item in (command, wrapper, collected)}),
                     domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(collected.id) as result:
            assert result.output('outcomes')[0].outcome == outcome
            assert result.outcome not in {'succeeded', 'partial'}
            assert 'items' not in result.outputs


def test_compiled_map_expands_member_scope_under_its_structural_task():
    command, wrapper = report_definitions('succeeded', 'data')
    mapped = OperationDefinition('operation.test.valid_map', outputs={'items': PortContract('result_collection', tuple)},
        body=GraphBody((MapCall('map', wrapper.id, (7,), output_port='value'),),
                      {'items': OutputRef('map', 'items')}))
    with StrategyBox(catalog=Catalog({item.id: item for item in (command, wrapper, mapped)}),
                     domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(mapped.id) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert result.output('items') == (7,)


@pytest.mark.parametrize('obligation', ('required_effects', 'required_completions'))
def test_independently_accepted_early_output_remains_consumable_after_later_member_failure(obligation):
    early = CommandDefinition('command.test.early', inputs={'item': INT}, outputs={'value': INT},
        method=MethodRef(__name__ + ':early_value'), reuse=NO_REUSE)
    late = CommandDefinition('command.test.late', inputs={'item': INT}, outputs={'value': INT},
        method=MethodRef(__name__ + ':late_completion'), reuse=NO_REUSE)
    member = OperationDefinition('operation.test.early_member', inputs={'item': INT}, outputs={'value': INT},
        body=GraphBody((Call('early', early.id, {'item': InputRef('item')}),
                        Call('late', late.id, {'item': OutputRef('early', 'value')})),
                       {'value': OutputRef('early', 'value')}, **{obligation: ('late',)}))
    outer = OperationDefinition('operation.test.use_early', outputs={'value': INT},
        body=GraphBody((Call('member', member.id, {'item': -1}),
                        Call('consume', early.id, {'item': OutputRef('member', 'value')})),
                       {'value': OutputRef('consume', 'value')}))
    with StrategyBox(catalog=Catalog({item.id: item for item in (early, late, member, outer)}),
                     domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(outer.id) as result:
            assert result.outcome == 'failed'
            assert result.output('value') == -1, result.diagnostics
            facts = box.session.journal.read(run_id=result.run_id)
            accepted = [fact for fact in facts if fact.kind == 'output.accepted' and fact.scope_id == 'root/consume']
            assert accepted


@pytest.mark.parametrize('outcome', ('failed', 'unknown'))
def test_prepared_map_assesses_selected_output_origin_in_addition_to_required_tasks(outcome):
    command = BoundCommand('command.test.origin_report', MethodRef(__name__ + ':reported_value'), {},
        {'item': INT}, {'value': PortContract('integer', int, outcomes=ALL_OUTCOMES)},
        parameters={'outcome': outcome}, reuse=NO_REUSE)
    template = PreparedPlan('member', (CommandTask('report', command, {'item': TemplateInput('item')}, required=False),),
        (), {'value': ValueRef('report')}, 'template', 'test')
    mapped = MapTask('map', template, (7,), item_output='value')
    prepared = PreparedPlan('batch', (mapped,), (),
        {'items': ValueRef('map', 'items'), 'outcomes': ValueRef('map', 'outcomes')}, 'batch', 'test')
    with ExecutionService() as service:
        with service.run(prepared, timeout=3) as result:
            assert result.output('outcomes')[0].outcome == outcome
            assert result.outcome not in {'succeeded', 'partial'}
            assert result.output('items') == ()


@pytest.mark.parametrize('obligation', ('required_checks', 'required_effects', 'required_completions'))
def test_eligible_subset_retains_each_optional_members_internal_obligations(obligation):
    early = CommandDefinition('command.test.early', inputs={'item': INT}, outputs={'value': INT},
        method=MethodRef(__name__ + ':early_value'), reuse=NO_REUSE)
    late = CommandDefinition('command.test.late', inputs={'item': INT}, outputs={'value': INT},
        method=MethodRef(__name__ + ':late_completion'), reuse=NO_REUSE)
    member = OperationDefinition('operation.test.member', inputs={'item': INT}, outputs={'value': INT},
        body=GraphBody((Call('early', early.id, {'item': InputRef('item')}),
                        Call('late', late.id, {'item': OutputRef('early', 'value')})),
                       {'value': OutputRef('early', 'value')}, **{obligation: ('late',)}))
    batch = OperationDefinition('operation.test.subset', outputs={
        'items': PortContract('result_collection', tuple),
        'outcomes': PortContract('unit_outcomes', tuple, role='diagnostic', outcomes=ALL_OUTCOMES)},
        body=GraphBody((Call('good', member.id, {'item': 1}, required=False),
                        Call('bad', member.id, {'item': -1}, required=False),
                        CollectCall('collect', (OutputRef('good', 'value'), OutputRef('bad', 'value')),
                                    min_items=1, completion='eligible_subset')),
                       {'items': OutputRef('collect', 'items'), 'outcomes': OutputRef('collect', 'outcomes')}))
    with StrategyBox(catalog=Catalog({item.id: item for item in (early, late, member, batch)}),
                     domains=DomainCatalog({}), build_identity='test') as box:
        with box.invoke(batch.id) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert result.output('items') == (1,)
            assert tuple(item.outcome for item in result.output('outcomes')) == ('succeeded', 'failed')


GENERATION_STARTED, GENERATION_RELEASE = Event(), Event()
GENERATION_LOCK = Lock()
GENERATION_CALLS = []


def pending_cancel_generation(inputs, settings, context):
    with GENERATION_LOCK:
        ordinal = len(GENERATION_CALLS) + 1
        GENERATION_CALLS.append(ordinal)
    if ordinal == 1:
        GENERATION_STARTED.set()
        assert GENERATION_RELEASE.wait(5)
    return {'value': ordinal}


def test_pending_cancelled_physical_generation_cannot_accept_new_demand():
    GENERATION_STARTED.clear(); GENERATION_RELEASE.clear(); GENERATION_CALLS.clear()
    command = BoundCommand('command.test.pending_cancel', MethodRef(__name__ + ':pending_cancel_generation'), {}, {},
        {'value': INT}, reuse=ReuseContract(shareable=True, completed=False))
    prepared = PreparedPlan('generation', (CommandTask('work', command, {}),), (),
        {'value': ValueRef('work')}, 'generation', 'test')
    with ExecutionService(settings=ExecutionSettings(max_workers=2)) as service:
        first = service.submit(prepared)
        try:
            assert GENERATION_STARTED.wait(2)
            assert first.cancel()
            with service.submit(prepared).result(timeout=2) as second:
                assert second.outcome == 'succeeded'
                assert second.output() == 2
            assert GENERATION_CALLS == [1, 2]
        finally:
            GENERATION_RELEASE.set()
            with first.result(timeout=3) as cancelled:
                assert cancelled.outcome == 'cancelled'
