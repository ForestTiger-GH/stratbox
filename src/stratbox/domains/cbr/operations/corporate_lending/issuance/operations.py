"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.corporate_lending.issuance.operations as _methods
from stratbox.domains.cbr.methods.corporate_lending.issuance.operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def discover(request: DiscoverIssuanceRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.discover'), request, lambda req, invocation: _methods.discover(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def acquire(request: IssuanceSourceLink, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def parse(request: ParseIssuanceRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.parse'), request, lambda req, invocation: _methods.parse(req, invocation=invocation), context=context)

def build_stream(request: BuildIssuanceStreamRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.build_stream'), request, lambda req, invocation: _methods.build_stream(req, invocation=invocation), context=context)

def calculate_apk(request: CalculateIssuanceApkRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.calculate_apk'), request, lambda req, invocation: _methods.calculate_apk(req, invocation=invocation), context=context)

def build_pivots(request: PivotIssuanceRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.build_pivots'), request, lambda req, invocation: _methods.build_pivots(req, invocation=invocation), context=context)

def render_industry(request: IssuanceWorkbookRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.render_industry'), request, lambda req, invocation: _methods.render_industry(req, invocation=invocation), context=context)

def render_industries(request: RenderIssuanceIndustriesRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.render_industries'), request, lambda req, invocation: _methods.render_industries(req, invocation=invocation), context=context)

def render_pivots(request, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0104a.render_pivots'), request, lambda req, invocation: _methods.render_pivots(req, invocation=invocation), context=context)
