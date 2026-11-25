"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.service_network.territorial_offices.snapshots as _methods
from stratbox.domains.cbr.methods.service_network.territorial_offices.snapshots import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def snapshot_release(request, *, context=None):
    return run(_definition('cbr.offices_reg.snapshot'), request, lambda req, invocation: _methods.snapshot_release(req, invocation=invocation), context=context)

def restore_release(request, *, context=None):
    return run(_definition('cbr.offices_reg.restore'), request, lambda req, invocation: _methods.restore_release(req, invocation=invocation), context=context)
