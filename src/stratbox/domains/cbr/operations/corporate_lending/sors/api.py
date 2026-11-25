"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.corporate_lending.sors.api as _methods
from stratbox.domains.cbr.methods.corporate_lending.sors.api import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def read_source_files(request: SorsSourceFiles, *, store: FileStore | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.sors.read_source_files'), request, lambda req, invocation: _methods.read_source_files(req, invocation=invocation, store=store), context=context, providers={'filestore': store})

def prepare_from_originals(request: PrepareSorsOriginalsRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.sors.prepare_from_originals'), request, lambda req, invocation: _methods.prepare_from_originals(req, invocation=invocation), context=context)

def restore(request: RestoreSorsRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.sors.restore'), request, lambda req, invocation: _methods.restore(req, invocation=invocation), context=context)

def restore_from_originals(request, *, context=None):
    return run(_definition('cbr.sors.restore_from_originals'), request, lambda req, invocation: _methods.restore_from_originals(req, invocation=invocation), context=context)

def prepare_inputs(request, *, context=None):
    return run(_definition('cbr.sors.prepare_inputs'), request, lambda req, invocation: _methods.prepare_inputs(req, invocation=invocation), context=context)

def prepare_from_flakes(request, *, context=None):
    return run(_definition('cbr.sors.prepare_from_flakes'), request, lambda req, invocation: _methods.prepare_from_flakes(req, invocation=invocation), context=context)

def run_crosswalk(request: CrosswalkSorsRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.sors.crosswalk'), request, lambda req, invocation: _methods.run_crosswalk(req, invocation=invocation), context=context)

def build_pivot(request: PivotSorsRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.sors.build_pivot'), request, lambda req, invocation: _methods.build_pivot(req, invocation=invocation), context=context)

def build_views(request, *, context=None):
    return run(_definition('cbr.sors.build_views'), request, lambda req, invocation: _methods.build_views(req, invocation=invocation), context=context)

def render_views(request: RenderSorsRequest, *, context=None):
    return run(_definition('cbr.sors.render_views'), request, lambda req, invocation: _methods.render_views(req, invocation=invocation), context=context)
