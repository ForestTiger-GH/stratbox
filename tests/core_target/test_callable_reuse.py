"""Opaque callable state can execute but cannot claim equivalent physical work."""
from functools import partial

import pytest

from stratbox.capabilities.model import MethodRef, PortContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution import ExecutionService
from stratbox.core.execution.code_identity import code_identity


def offset(inputs, settings, context, *, amount):
    return {'value': inputs['value'] + amount}


first = partial(offset, amount=10)
second = partial(offset, amount=20)


class Configured:
    def __init__(self, amount):
        self.amount = amount

    def __call__(self, inputs, settings, context):
        return {'value': inputs['value'] + self.amount}


@pytest.mark.parametrize('value', [first, second, Configured(10), Configured(20).__call__, [].append])
def test_opaque_callable_does_not_advertise_exact_code_identity(value):
    with pytest.raises(TypeError, match='opaque_callable_state'):
        code_identity(value)


def test_partial_methods_with_distinct_captured_settings_cannot_reuse():
    port = PortContract('integer', int)
    def plan(locator):
        command = BoundCommand('command.test.partial', MethodRef(__name__ + ':' + locator),
            None, {'value': port}, {'value': port})
        return PreparedPlan('test', (CommandTask('work', command, {'value': 1}),), (),
            {'value': ValueRef('work')}, 'test', 'build')
    with ExecutionService() as service:
        with service.run(plan('first')) as a, service.run(plan('second')) as b:
            assert a.output() == 11
            assert b.output() == 21
