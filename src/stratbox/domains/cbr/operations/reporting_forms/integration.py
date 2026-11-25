"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.integration as _methods
from stratbox.domains.cbr.methods.reporting_forms.integration import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def align_forms(request, *, context=None):
    return run(_definition('cbr.forms.align'), request, lambda req, invocation: _methods.align_forms(req, invocation=invocation), context=context)
