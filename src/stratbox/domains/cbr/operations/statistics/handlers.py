"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.statistics.handlers as _methods
from stratbox.domains.cbr.methods.statistics.handlers import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def extract(request, *, context=None):
    return run(_definition('cbr.tables.extract'), request, lambda req, invocation: _methods.extract(req, invocation=invocation), context=context)

def validate(request, *, context=None):
    return run(_definition('cbr.tables.validate'), request, lambda req, invocation: _methods.validate(req, invocation=invocation), context=context)

def compare(request, *, context=None):
    return run(_definition('cbr.tables.compare'), request, lambda req, invocation: _methods.compare(req, invocation=invocation), context=context)

def readable(request, *, context=None):
    return run(_definition('cbr.tables.readable'), request, lambda req, invocation: _methods.readable(req, invocation=invocation), context=context)

def build_flake_snapshot(request, *, context=None):
    return run(_definition('cbr.tables.flake_snapshot'), request, lambda req, invocation: _methods.build_flake_snapshot(req, invocation=invocation), context=context)

def read_flake_snapshot(request, *, context=None):
    return run(_definition('cbr.tables.read_flake_snapshot'), request, lambda req, invocation: _methods.read_flake_snapshot(req, invocation=invocation), context=context)

def align(request, *, context=None):
    return run(_definition('cbr.statistics.align'), request, lambda req, invocation: _methods.align(req, invocation=invocation), context=context)

def calculate_change(request, *, context=None):
    return run(_definition('cbr.statistics.calculate_change'), request, lambda req, invocation: _methods.calculate_change(req, invocation=invocation), context=context)

def calculate_share(request, *, context=None):
    return run(_definition('cbr.statistics.calculate_share'), request, lambda req, invocation: _methods.calculate_share(req, invocation=invocation), context=context)

def build_view(request, *, context=None):
    return run(_definition('cbr.statistics.build_view'), request, lambda req, invocation: _methods.build_view(req, invocation=invocation), context=context)

def render_view(request, *, context=None):
    return run(_definition('cbr.statistics.render_view'), request, lambda req, invocation: _methods.render_view(req, invocation=invocation), context=context)

def build_dataset_snapshot(request, *, context=None):
    return run(_definition('cbr.statistics.dataset_snapshot'), request, lambda req, invocation: _methods.build_dataset_snapshot(req, invocation=invocation), context=context)

def read_dataset_snapshot(request, *, context=None):
    return run(_definition('cbr.statistics.read_dataset_snapshot'), request, lambda req, invocation: _methods.read_dataset_snapshot(req, invocation=invocation), context=context)

def build_view_snapshot(request, *, context=None):
    return run(_definition('cbr.statistics.view_snapshot'), request, lambda req, invocation: _methods.build_view_snapshot(req, invocation=invocation), context=context)

def read_view_snapshot(request, *, context=None):
    return run(_definition('cbr.statistics.read_view_snapshot'), request, lambda req, invocation: _methods.read_view_snapshot(req, invocation=invocation), context=context)
