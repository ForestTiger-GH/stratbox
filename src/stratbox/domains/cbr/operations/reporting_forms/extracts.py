"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.extracts as _methods
from stratbox.domains.cbr.methods.reporting_forms.extracts import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def discover_sources(request, *, transport=None, context=None):
    return run(_definition('cbr.forms.discover_sources'), request, lambda req, invocation: _methods.discover_sources(req, invocation=invocation, transport=transport), providers={'http': transport}, context=context)

def extract_forms(request, *, rar_reader=None, context=None):
    return run(_definition('cbr.forms.extract'), request, lambda req, invocation: _methods.extract_forms(req, invocation=invocation, rar_reader=rar_reader), context=context)

def normalize_form(request, *, context=None):
    return run(_definition('cbr.forms.normalize'), request, lambda req, invocation: _methods.normalize_form(req, invocation=invocation), context=context)

def flake_snapshot(request, *, context=None):
    return run(_definition('cbr.forms.flake_snapshot'), request, lambda req, invocation: _methods.flake_snapshot(req, invocation=invocation), context=context)

def restore_flakes(request, *, context=None):
    return run(_definition('cbr.forms.restore_flakes'), request, lambda req, invocation: _methods.restore_flakes(req, invocation=invocation), context=context)

def snapshot_result(request, *, context=None):
    return run(_definition('cbr.forms.result_snapshot'), request, lambda req, invocation: _methods.snapshot_result(req, invocation=invocation), context=context)

def restore_normalized(request, *, context=None):
    return run(_definition('cbr.forms.restore_normalized'), request, lambda req, invocation: _methods.restore_normalized(req, invocation=invocation), context=context)

def restore_data(request, *, context=None):
    return run(_definition('cbr.forms.restore_data'), request, lambda req, invocation: _methods.restore_data(req, invocation=invocation), context=context)

def restore_views(request, *, context=None):
    return run(_definition('cbr.forms.restore_views'), request, lambda req, invocation: _methods.restore_views(req, invocation=invocation), context=context)

def build_source_history(request, *, context=None):
    return run(_definition('cbr.forms.build_history'), request, lambda req, invocation: _methods.build_source_history(req, invocation=invocation), context=context)

def restore_history(request, *, context=None):
    return run(_definition('cbr.forms.restore_history'), request, lambda req, invocation: _methods.restore_history(req, invocation=invocation), context=context)

def parse_form(request: ParseFormRequest, *, rar_reader: ArchiveReader | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.parse'), request, lambda req, invocation: _methods.parse_form(req, invocation=invocation, rar_reader=rar_reader), context=context)
