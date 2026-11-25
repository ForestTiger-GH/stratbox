"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.project_finance.lifecycle as _methods
from stratbox.domains.cbr.methods.project_finance.lifecycle import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def integrate_flakes(request, *, context=None):
    return run(_definition('cbr.escrow.integrate_flakes'), request, lambda req, invocation: _methods.integrate_flakes(req, invocation=invocation), context=context)

def build_flake_snapshot(request, *, context=None):
    return run(_definition('cbr.escrow.flake_snapshot'), request, lambda req, invocation: _methods.build_flake_snapshot(req, invocation=invocation), context=context)

def read_flake_snapshot(request, *, context=None):
    return run(_definition('cbr.escrow.read_flake_snapshot'), request, lambda req, invocation: _methods.read_flake_snapshot(req, invocation=invocation), context=context)

def build_dataset_snapshot(request, *, context=None):
    return run(_definition('cbr.escrow.dataset_snapshot'), request, lambda req, invocation: _methods.build_dataset_snapshot(req, invocation=invocation), context=context)

def read_dataset_snapshot(request, *, context=None):
    return run(_definition('cbr.escrow.read_dataset_snapshot'), request, lambda req, invocation: _methods.read_dataset_snapshot(req, invocation=invocation), context=context)

def build_view_snapshot(request, *, context=None):
    return run(_definition('cbr.escrow.view_snapshot'), request, lambda req, invocation: _methods.build_view_snapshot(req, invocation=invocation), context=context)

def read_view_snapshot(request, *, context=None):
    return run(_definition('cbr.escrow.read_view_snapshot'), request, lambda req, invocation: _methods.read_view_snapshot(req, invocation=invocation), context=context)
