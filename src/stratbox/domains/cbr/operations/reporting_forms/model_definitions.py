"""Typed admission and calculation boundaries for retained semantic observations."""

from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.analytics.reporting_forms.contracts import (
    PrepareFormModelInputsRequest, FormModelInputs, CalculateFormRequest, FormData,
)
from .definitions import _TABLES

PREPARE = _registry_definition('cbr.forms.prepare_model_inputs', 1)
CALCULATE = _registry_definition('cbr.forms.calculate', 1)
