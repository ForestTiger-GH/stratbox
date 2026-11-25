"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.source_products as _methods
from stratbox.domains.cbr.methods.reporting_forms.source_products import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def compare_sources(request, *, context=None):
    return run(_definition('cbr.forms.compare'), request, lambda req, invocation: _methods.compare_sources(req, invocation=invocation), context=context)

def make_readable(request, *, context=None):
    return run(_definition('cbr.forms.make_readable'), request, lambda req, invocation: _methods.make_readable(req, invocation=invocation), context=context)
