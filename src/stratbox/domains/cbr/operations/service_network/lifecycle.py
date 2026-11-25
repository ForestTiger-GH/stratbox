"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.service_network.lifecycle as _methods
from stratbox.domains.cbr.methods.service_network.lifecycle import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def make_readable(request, *, context=None):
    return run(_definition('cbr.service_network.make_readable'), request, lambda req, invocation: _methods.make_readable(req, invocation=invocation), context=context)

def build_source_history(request, *, context=None):
    return run(_definition('cbr.service_network.build_history'), request, lambda req, invocation: _methods.build_source_history(req, invocation=invocation), context=context)

def restore_history(request, *, context=None):
    return run(_definition('cbr.service_network.restore_history'), request, lambda req, invocation: _methods.restore_history(req, invocation=invocation), context=context)

def align_offices(request, *, context=None):
    return run(_definition('cbr.service_network.align'), request, lambda req, invocation: _methods.align_offices(req, invocation=invocation), context=context)

def calculate_changes(request, *, context=None):
    return run(_definition('cbr.service_network.calculate_changes'), request, lambda req, invocation: _methods.calculate_changes(req, invocation=invocation), context=context)

def build_view(request, *, context=None):
    return run(_definition('cbr.service_network.build_view'), request, lambda req, invocation: _methods.build_view(req, invocation=invocation), context=context)

def render(request, *, context=None):
    return run(_definition('cbr.service_network.render'), request, lambda req, invocation: _methods.render(req, invocation=invocation), context=context)
