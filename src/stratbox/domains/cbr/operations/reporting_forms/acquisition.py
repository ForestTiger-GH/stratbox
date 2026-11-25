"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.acquisition as _methods
from stratbox.domains.cbr.methods.reporting_forms.acquisition import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def select_sources(request: SelectFormSourcesRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.select_sources'), request, lambda req, invocation: _methods.select_sources(req, invocation=invocation), context=context)

def acquire(request: FormKey, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)
