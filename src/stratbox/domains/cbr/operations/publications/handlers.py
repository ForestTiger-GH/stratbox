"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.publications.handlers as _methods
from stratbox.domains.cbr.methods.publications.handlers import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def list_sources(request, *, context=None):
    return run(_definition('cbr.publications.list_sources'), request, lambda req, invocation: _methods.list_sources(req, invocation=invocation), context=context)

def discover(request, *, transport=None, selection=None, context=None):
    return run(_definition('cbr.publications.discover'), request, lambda req, invocation: _methods.discover(req, invocation=invocation, transport=transport, selection=selection), context=context, providers={'http': transport}, provider_selections={'http': selection} if selection is not None else None)

def identify(request, *, context=None):
    return run(_definition('cbr.publications.identify'), request, lambda req, invocation: _methods.identify(req, invocation=invocation), context=context)

def select(request, *, context=None):
    return run(_definition('cbr.publications.select'), request, lambda req, invocation: _methods.select(req, invocation=invocation), context=context)

def acquire(request, *, transport=None, selection=None, context=None):
    return run(_definition('cbr.publications.acquire'), request, lambda req, invocation: _methods.acquire(req, invocation=invocation, transport=transport, selection=selection), context=context, providers={'http': transport}, provider_selections={'http': selection} if selection is not None else None)

def assess_updates(request, *, context=None):
    return run(_definition('cbr.publications.assess_updates'), request, lambda req, invocation: _methods.assess_updates(req, invocation=invocation), context=context)
