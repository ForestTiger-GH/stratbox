"""Public semantic alignment independent of source extraction and model evaluation."""
from stratbox.core.execution import run
from stratbox.domains.cbr.integration.reporting_forms.alignment import align
from .integration_definitions import ALIGN

def align_forms(request, *, context=None):
    return run(ALIGN, request, align, context=context)
