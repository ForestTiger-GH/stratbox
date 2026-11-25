"""Ordered bounded folds retain state, retries and ordinary admission scopes."""
from collections import Counter

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    CommandDefinition, OperationDefinition, ScenarioDefinition, PortContract,
    GraphBody, Call, FoldCall, InputRef, OutputRef, ParameterRef, RetryPolicy, ReuseContract,
)
from stratbox.core.execution.contracts import OperationFailure
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract

class Counters:
    calls = Counter()

CALLS = Counters.calls
NUMBER = PortContract(DataContract('fold.number'), int)
ITEMS = PortContract(DataContract('fold.numbers'), tuple, collection=True)


def zero(request, invocation):
    return 0


def add(request, invocation):
    Counters.calls[request['item']] += 1
    if request['item'] == 2 and Counters.calls[2] == 1:
        raise OperationFailure('fixture.transient')
    return request['state'] + request['item']


def snapshot():
    commands = (
        CommandDefinition('fold.zero', __name__ + ':zero', outputs={'value': NUMBER}),
        CommandDefinition('fold.add', __name__ + ':add', inputs={'state': NUMBER, 'item': NUMBER},
            outputs={'value': NUMBER}, reuse=ReuseContract(shareable=False)))
    operations = (
        OperationDefinition('fold.initialize', GraphBody((Call('zero', 'fold.zero'),),
            {'value': OutputRef('zero')}), outputs={'value': NUMBER}),
        OperationDefinition('fold.transition', GraphBody((Call('add', 'fold.add',
            {'state': InputRef('state'), 'item': InputRef('item')}),), {'value': OutputRef('add')}),
            inputs={'state': NUMBER, 'item': NUMBER}, outputs={'value': NUMBER}))
    member = ScenarioDefinition('fold.member', GraphBody((Call('step', 'fold.transition',
        {'state': InputRef('state'), 'item': InputRef('item')}),), {'value': OutputRef('step')}),
        inputs={'state': NUMBER, 'item': NUMBER}, outputs={'value': NUMBER})
    route = ScenarioDefinition('fold.sum', GraphBody((
        Call('initialize', 'fold.initialize'),
        FoldCall('members', 'fold.member', InputRef('items'), OutputRef('initialize'), NUMBER,
                 retry=ParameterRef('retry'), max_items=3),
    ), {'value': OutputRef('members')}), inputs={'items': ITEMS}, outputs={'value': NUMBER},
        parameters={'retry': RetryPolicy(2, retry_codes=('fixture.transient',))})
    return CatalogSnapshot(definitions=(*commands, *operations, member, route))


def test_each_member_is_scheduled_separately_and_only_failed_member_retries():
    CALLS.clear()
    with StrategyBox(capabilities=snapshot()) as box:
        plan = box.prepare('fold.sum', inputs={'items': (1, 2, 3)})
        result = box.run(plan, timeout=5)
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('value') == 6
        assert CALLS == {1: 1, 2: 2, 3: 1}
        assert len([scope for scope in plan.scopes if scope.definition_id == 'fold.member']) == 3
        assert all(task.capability_kind in {'command', 'operation', 'scenario'} for task in plan.tasks)


def test_empty_fold_preserves_initialized_state_and_limit_admission_precedes_work():
    CALLS.clear()
    with StrategyBox(capabilities=snapshot()) as box:
        result = box.invoke('fold.sum', inputs={'items': ()}, timeout=5)
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('value') == 0
        assert not CALLS
        with pytest.raises(ValueError, match='composition.fold_item_limit'):
            box.prepare('fold.sum', inputs={'items': (1, 2, 3, 4)})
        assert not CALLS
