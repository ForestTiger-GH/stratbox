"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.service_network.bank_offices.operations as _methods
from stratbox.domains.cbr.methods.service_network.bank_offices.operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def acquire(request: AcquireOfficesRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)

def parse(request: ParseOfficesRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices.parse'), request, lambda req, invocation: _methods.parse(req, invocation=invocation), context=context)

def capture(request: AcquireOfficesRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices.capture'), request, lambda req, invocation: _methods.capture(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)

def read_representation(request: ReadOfficesRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices.read_representation'), request, lambda req, invocation: _methods.read_representation(req, invocation=invocation), context=context)

def compare(request: CompareReleaseRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.offices.compare'), request, lambda req, invocation: _methods.compare(req, invocation=invocation), context=context)
