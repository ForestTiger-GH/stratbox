"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.service_network.territorial_offices.operations as _methods
from stratbox.domains.cbr.methods.service_network.territorial_offices.operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def discover(request: DiscoverOfficesRegRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices_reg.discover'), request, lambda req, invocation: _methods.discover(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)

def acquire(request: ReleaseLink, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices_reg.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)

def parse(request: ParseOfficesRegRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices_reg.parse'), request, lambda req, invocation: _methods.parse(req, invocation=invocation), context=context)

def capture(request: ReleaseLink, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices_reg.capture'), request, lambda req, invocation: _methods.capture(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)

def read_representation(request: ReadOfficesRegRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices_reg.read_representation'), request, lambda req, invocation: _methods.read_representation(req, invocation=invocation), context=context)

def compare(request: CompareReleaseRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices_reg.compare'), request, lambda req, invocation: _methods.compare(req, invocation=invocation), context=context)
