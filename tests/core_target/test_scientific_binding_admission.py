"""Physical sharing cannot substitute for a logical scientific competence gate."""
from dataclasses import replace
from threading import Event

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution import ExecutionService


ENTERED, RELEASE = Event(), Event()
CALLS = []


def evaluate(inputs, settings, context):
    CALLS.append(context.run_id)
    ENTERED.set()
    assert RELEASE.wait(3)
    return {'value': inputs['value']}


@pytest.mark.parametrize('completed', (False, True))
def test_declared_scientific_limit_blocks_both_completed_reuse_and_inflight_join(completed):
    ENTERED.clear(); RELEASE.clear(); CALLS.clear()
    command = BoundCommand('command.test.scientific', MethodRef(__name__ + ':evaluate'), {},
        {'value': PortContract('number', int)}, {'value': PortContract('number', int)},
        reuse=ReuseContract())
    ready = PreparedPlan('test', (CommandTask('work', command, {'value': 7}),), (),
        {'value': ValueRef('work')}, 'test', 'test')
    blocked = replace(ready, tasks=(replace(ready.tasks[0], command=replace(command,
        scientific_limitations=('required_scientific_model',))),))
    with ExecutionService() as service:
        first = service.submit(ready)
        try:
            assert ENTERED.wait(2)
            if completed:
                RELEASE.set()
                assert first.result(2).outcome == 'succeeded'
            with service.submit(blocked).result(2) as result:
                assert result.outcome == 'failed'
                assert result.diagnostics == ('scientific.binding_unavailable:required_scientific_model',)
                assert not result.outputs
            assert len(CALLS) == 1
        finally:
            RELEASE.set()
            first.result(3).close()
