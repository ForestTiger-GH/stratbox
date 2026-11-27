"""A physical key contains actual bound values, never unresolved graph syntax."""
from threading import Event, current_thread

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution import ExecutionService
from stratbox.shared.data.values import SourceDataset


ENTERED, RELEASE = Event(), Event()
CALLS = []


def source(inputs, settings, context):
    return {'value': inputs['value']}


def consume_parameter(inputs, settings, context):
    value = context.parameters['selected']
    CALLS.append(value)
    if value == 1:
        ENTERED.set()
        assert RELEASE.wait(3)
    return {'value': value}


def constant(inputs, settings, context):
    return {'value': 7}


def prepared(value):
    integer = PortContract('number', int)
    producer = BoundCommand('command.test.parameter_source', MethodRef(__name__ + ':source'), {},
        {'value': integer}, {'value': integer})
    consumer = BoundCommand('command.test.parameter_consumer', MethodRef(__name__ + ':consume_parameter'), {},
        {}, {'value': integer}, parameters={'selected': ValueRef('source')}, reuse=ReuseContract())
    return PreparedPlan('test', (CommandTask('source', producer, {'value': value}),
        CommandTask('consumer', consumer, {})), (), {'value': ValueRef('consumer')}, 'test', 'test')


@pytest.mark.parametrize('completed', (False, True))
def test_changed_resolved_parameter_never_reuses_or_joins_the_previous_value(completed):
    ENTERED.clear(); RELEASE.clear(); CALLS.clear()
    with ExecutionService() as service:
        first = service.submit(prepared(1))
        try:
            assert ENTERED.wait(2)
            if completed:
                RELEASE.set()
                assert first.result(2).output() == 1
            with service.submit(prepared(2)).result(2) as second:
                assert second.outcome == 'succeeded', second.diagnostics
                assert second.output() == 2
            assert CALLS == [1, 2]
        finally:
            RELEASE.set()
            first.result(3).close()


def test_settings_parameters_and_fallback_target_keys_use_admitted_descriptors(monkeypatch):
    import stratbox.shared.data.value_identity as identities
    original = identities.exact_fingerprint
    seen = []
    def measured(value, **kwargs):
        if isinstance(value, SourceDataset): seen.append(current_thread().name)
        return original(value, **kwargs)
    monkeypatch.setattr(identities, 'exact_fingerprint', measured)
    payload = SourceDataset('fixture', tuple({'value': index} for index in range(128)))
    command = BoundCommand('command.test.parameter_identity', MethodRef(__name__ + ':constant'), payload,
        {}, {'value': PortContract('number', int)}, parameters={'literal': payload})
    plan = PreparedPlan('test', (CommandTask('work', command, {}),), (),
        {'value': ValueRef('work')}, 'test', 'test', target=payload)
    with ExecutionService() as service:
        with service.run(plan) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            assert result.output() == 7
    assert seen and 'stratbox-coordinator' not in seen
