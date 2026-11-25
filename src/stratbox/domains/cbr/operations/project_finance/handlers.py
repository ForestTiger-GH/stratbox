"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.project_finance.handlers as _methods
from stratbox.domains.cbr.methods.project_finance.handlers import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def discover(request: DiscoverEscrowRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.escrow.discover'), request, lambda req, invocation: _methods.discover(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def acquire(request: EscrowSourceLink, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.escrow.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def parse(request: ParseEscrowRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.escrow.parse'), request, lambda req, invocation: _methods.parse(req, invocation=invocation), context=context)

def build_history(request: EscrowHistoryBuildRequest, *, context=None):
    return run(_definition('cbr.escrow.build_history'), request, lambda req, invocation: _methods.build_history(req, invocation=invocation), context=context)

def build_views(request: BuildEscrowViewsRequest, *, context=None):
    return run(_definition('cbr.escrow.build_views'), request, lambda req, invocation: _methods.build_views(req, invocation=invocation), context=context)

def render_workbook(request: EscrowPivotPack, *, context=None):
    return run(_definition('cbr.escrow.render_workbook'), request, lambda req, invocation: _methods.render_workbook(req, invocation=invocation), context=context)
