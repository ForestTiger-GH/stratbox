"""Output ownership accounts for buffer bodies and nested object-cell payloads."""
import numpy as np
import pandas as pd
import pytest

from stratbox.capabilities.model import MethodRef, PortContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution.service import ExecutionService, ExecutionSettings
from stratbox.core.execution.owned_values import _size
from stratbox.core.limits import ExecutionBudget


def large_buffer(inputs, settings, context):
    return {'value': memoryview(bytes(8192))}


def test_output_buffer_cannot_bypass_the_boundary_budget():
    command = BoundCommand('command.test.buffer', MethodRef(__name__ + ':large_buffer'),
        None, {}, {'value': PortContract('buffer', memoryview)})
    plan = PreparedPlan('test', (CommandTask('work', command, {}),), (),
        {'value': ValueRef('work')}, 'test', 'build')
    with ExecutionService(settings=ExecutionSettings(run_limits=ExecutionBudget(output_bytes=1024))) as service:
        result = service.run(plan)
        assert result.outcome == 'failed' and not result.outputs
        assert 'budget.output_bytes' in result.diagnostics


@pytest.mark.parametrize('kind', ['numpy', 'dataframe', 'series'])
def test_nested_object_buffers_count_their_payload_without_alias_duplication(kind):
    shared = bytearray(8192)
    array = np.empty(2, dtype=object)
    array[:] = [[shared], [shared]]
    value = array if kind == 'numpy' else pd.DataFrame({'objects': list(array)}) if kind == 'dataframe' else pd.Series(list(array))
    accounted = _size(value)
    assert 8192 <= accounted < 2 * 8192
