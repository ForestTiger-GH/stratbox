"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.corporate_lending.sors.snapshot_operations as _methods
from stratbox.domains.cbr.methods.corporate_lending.sors.snapshot_operations import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def build_bundle_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.bundle_snapshot'), request, lambda req, invocation: _methods.build_bundle_snapshot(req, invocation=invocation), context=context)

def read_bundle_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.read_bundle_snapshot'), request, lambda req, invocation: _methods.read_bundle_snapshot(req, invocation=invocation), context=context)

def build_restoration_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.restoration_snapshot'), request, lambda req, invocation: _methods.build_restoration_snapshot(req, invocation=invocation), context=context)

def read_restoration_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.read_restoration_snapshot'), request, lambda req, invocation: _methods.read_restoration_snapshot(req, invocation=invocation), context=context)

def build_crosswalk_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.crosswalk_snapshot'), request, lambda req, invocation: _methods.build_crosswalk_snapshot(req, invocation=invocation), context=context)

def read_crosswalk_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.read_crosswalk_snapshot'), request, lambda req, invocation: _methods.read_crosswalk_snapshot(req, invocation=invocation), context=context)

def build_view_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.view_snapshot'), request, lambda req, invocation: _methods.build_view_snapshot(req, invocation=invocation), context=context)

def read_view_snapshot(request, *, context=None):
    return run(_definition('cbr.sors.read_view_snapshot'), request, lambda req, invocation: _methods.read_view_snapshot(req, invocation=invocation), context=context)
