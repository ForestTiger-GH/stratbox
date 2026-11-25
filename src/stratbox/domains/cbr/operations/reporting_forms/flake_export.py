"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.flake_export as _methods
from stratbox.domains.cbr.methods.reporting_forms.flake_export import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def render_flakes(request, *, context=None):
    return run(_definition('cbr.forms.render_flakes'), request, lambda req, invocation: _methods.render_flakes(req, invocation=invocation), context=context)

def read_flake_export(request, *, context=None):
    return run(_definition('cbr.forms.read_flake_export'), request, lambda req, invocation: _methods.read_flake_export(req, invocation=invocation), context=context)
