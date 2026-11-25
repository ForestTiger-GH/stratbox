"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.corporate_lending.debt.operations as _methods
from stratbox.domains.cbr.methods.corporate_lending.debt.operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def discover(request: DiscoverIndustriesRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.discover'), request, lambda req, invocation: _methods.discover(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def acquire(request: Cbr0105ADebtCorpSourceLink, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def parse(request: ParseIndustryRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.parse'), request, lambda req, invocation: _methods.parse(req, invocation=invocation), context=context)

def build_stream(request: BuildIndustryStreamRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.build_stream'), request, lambda req, invocation: _methods.build_stream(req, invocation=invocation), context=context)

def calculate_apk(request: CalculateApkRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.calculate_apk'), request, lambda req, invocation: _methods.calculate_apk(req, invocation=invocation), context=context)

def build_pivots(request: PivotInput, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.build_pivots'), request, lambda req, invocation: _methods.build_pivots(req, invocation=invocation), context=context)

def render_pivots(request: RenderPivotRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.render_pivots'), request, lambda req, invocation: _methods.render_pivots(req, invocation=invocation), context=context)

def render_industry(request: RenderIndustryRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.render_industry'), request, lambda req, invocation: _methods.render_industry(req, invocation=invocation), context=context)

def render_industries(request: RenderIndustriesRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.industries.0105a.render_industries'), request, lambda req, invocation: _methods.render_industries(req, invocation=invocation), context=context)
