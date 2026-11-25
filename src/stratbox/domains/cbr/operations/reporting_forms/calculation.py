"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.reporting_forms.calculation as _methods
from stratbox.domains.cbr.methods.reporting_forms.calculation import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def prepare_model_inputs(request: PrepareFormModelInputsRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.prepare_model_inputs'), request, lambda req, invocation: _methods.prepare_model_inputs(req, invocation=invocation), context=context)

def calculate(request: CalculateFormRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.calculate'), request, lambda req, invocation: _methods.calculate(req, invocation=invocation), context=context)

def build_form_data(request: BuildFormDataRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.forms.build_data'), request, lambda req, invocation: _methods.build_form_data(req, invocation=invocation), context=context)
