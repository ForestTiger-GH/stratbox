"""Public semantic alignment independent of source extraction and model evaluation."""
from stratbox.domains.cbr.integration.reporting_forms.alignment import align
from stratbox.domains.cbr.operations.reporting_forms.integration_definitions import ALIGN

def align_forms(request, *, invocation=None):
    return align(request, invocation)


def capability_align_forms(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.align', align_forms)
