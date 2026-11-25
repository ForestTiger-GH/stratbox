"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.collection.materials as _methods
from stratbox.domains.cbr.methods.collection.materials import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def collect_materials(request, *, transport=None, store=None, context=None):
    return run(_definition('cbr.file_collector.collect_materials'), request, lambda req, invocation: _methods.collect_materials(req, invocation=invocation, transport=transport, store=store), context=context, providers={'http': transport, 'filestore': store})
