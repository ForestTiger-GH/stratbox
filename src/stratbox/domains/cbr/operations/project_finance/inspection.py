"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.project_finance.inspection as _methods
from stratbox.domains.cbr.methods.project_finance.inspection import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def validate(request, *, context=None):
    return run(_definition('cbr.escrow.validate'), request, lambda req, invocation: _methods.validate(req, invocation=invocation), context=context)

def compare(request, *, context=None):
    return run(_definition('cbr.escrow.compare'), request, lambda req, invocation: _methods.compare(req, invocation=invocation), context=context)

def readable(request, *, context=None):
    return run(_definition('cbr.escrow.readable'), request, lambda req, invocation: _methods.readable(req, invocation=invocation), context=context)

def align_observations(request, *, context=None):
    return run(_definition('cbr.escrow.align_observations'), request, lambda req, invocation: _methods.align_observations(req, invocation=invocation), context=context)
