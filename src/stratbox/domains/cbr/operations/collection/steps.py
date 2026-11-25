"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.collection.steps as _methods
from stratbox.domains.cbr.methods.collection.steps import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def collect_material_step(request, *, transport=None, store=None, context=None):
    return run(_definition('cbr.file_collector.collect_material_step'), request, lambda req, invocation: _methods.collect_material_step(req, invocation=invocation, transport=transport, store=store), context=context, providers={'http': transport, 'filestore': store})

def collect_stored_step(request, *, transport=None, store=None, context=None):
    return run(_definition('cbr.file_collector.collect_stored_step'), request, lambda req, invocation: _methods.collect_stored_step(req, invocation=invocation, transport=transport, store=store), context=context, providers={'http': transport, 'output_filestore': store})

def collect_raw_step(request, *, transport=None, context=None):
    return run(_definition('cbr.file_collector.collect_raw_step'), request, lambda req, invocation: _methods.collect_raw_step(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})
