"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.corporate_lending.debt.snapshot_operations as _methods
from stratbox.domains.cbr.methods.corporate_lending.debt.snapshot_operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def integrate_flakes(request, *, context=None):
    return run(_definition('cbr.industries.0105a.integrate_flakes'), request, lambda req, invocation: _methods.integrate_flakes(req, invocation=invocation), context=context)

def build_flake_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.flake_snapshot'), request, lambda req, invocation: _methods.build_flake_snapshot(req, invocation=invocation), context=context)

def read_flake_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.read_flake_snapshot'), request, lambda req, invocation: _methods.read_flake_snapshot(req, invocation=invocation), context=context)

def build_stream_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.stream_snapshot'), request, lambda req, invocation: _methods.build_stream_snapshot(req, invocation=invocation), context=context)

def read_stream_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.read_stream_snapshot'), request, lambda req, invocation: _methods.read_stream_snapshot(req, invocation=invocation), context=context)

def build_calculation_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.calculation_snapshot'), request, lambda req, invocation: _methods.build_calculation_snapshot(req, invocation=invocation), context=context)

def read_calculation_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.read_calculation_snapshot'), request, lambda req, invocation: _methods.read_calculation_snapshot(req, invocation=invocation), context=context)

def build_view_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.view_snapshot'), request, lambda req, invocation: _methods.build_view_snapshot(req, invocation=invocation), context=context)

def read_view_snapshot(request, *, context=None):
    return run(_definition('cbr.industries.0105a.read_view_snapshot'), request, lambda req, invocation: _methods.read_view_snapshot(req, invocation=invocation), context=context)
