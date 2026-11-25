"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.catalog.handlers as _methods
from stratbox.domains.cbr.methods.catalog.handlers import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def describe_source(request, *, context=None):
    return run(_definition('cbr.describe_source'), request, lambda req, invocation: _methods.describe_source(req, invocation=invocation), context=context)

def describe_family(request, *, context=None):
    return run(_definition('cbr.describe_family'), request, lambda req, invocation: _methods.describe_family(req, invocation=invocation), context=context)
