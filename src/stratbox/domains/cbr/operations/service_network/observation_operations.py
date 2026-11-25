"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.service_network.observation_operations as _methods
from stratbox.domains.cbr.methods.service_network.observation_operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def snapshot_observations(request, *, context=None):
    return run(_definition('cbr.service_network.observations_snapshot'), request, lambda req, invocation: _methods.snapshot_observations(req, invocation=invocation), context=context)

def restore_observations(request, *, context=None):
    return run(_definition('cbr.service_network.restore_observations'), request, lambda req, invocation: _methods.restore_observations(req, invocation=invocation), context=context)
