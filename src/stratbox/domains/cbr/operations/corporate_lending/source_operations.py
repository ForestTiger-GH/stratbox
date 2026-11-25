"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.corporate_lending.source_operations as _methods
from stratbox.domains.cbr.methods.corporate_lending.source_operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def extract(request, *, context=None):
    return run(_definition('cbr.corporate_lending.extract_observations'), request, lambda req, invocation: _methods.extract(req, invocation=invocation), context=context)

def build_snapshot(request, *, context=None):
    return run(_definition('cbr.corporate_lending.observation_snapshot'), request, lambda req, invocation: _methods.build_snapshot(req, invocation=invocation), context=context)

def read_snapshot(request, *, context=None):
    return run(_definition('cbr.corporate_lending.read_observation_snapshot'), request, lambda req, invocation: _methods.read_snapshot(req, invocation=invocation), context=context)
