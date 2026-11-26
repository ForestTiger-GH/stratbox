"""Default rejection for commands requiring a domain numerical specification."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure


def model_specification_required(inputs, settings, context):
    raise ExecutionFailure("calculation.model_specification_required")
