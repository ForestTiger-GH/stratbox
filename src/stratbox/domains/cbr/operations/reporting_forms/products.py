"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.products as _methods
from stratbox.domains.cbr.methods.reporting_forms.products import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def build_form_views(request: FormData, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.build_views'), request, lambda req, invocation: _methods.build_form_views(req, invocation=invocation), context=context)

def render_workbook(request: FormViews, *, style_registry=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.render_workbook'), request, lambda req, invocation: _methods.render_workbook(req, invocation=invocation, style_registry=style_registry), context=context)
