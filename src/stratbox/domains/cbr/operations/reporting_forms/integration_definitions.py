"""Lightweight semantic alignment metadata."""

from stratbox.operations.declarations import definition as _registry_definition
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.integration.reporting_forms.contracts import AlignFormRequest

ALIGN = _registry_definition('cbr.forms.align')
