"""Handlers for explicit validation, revision comparison and semantic mapping."""
from stratbox.core.execution import OperationFailure
from stratbox.domains.cbr.tables.project_finance.evidence import use_flake
from stratbox.domains.cbr.integration.project_finance.evidence import use_dataset
from stratbox.domains.cbr.operations.project_finance import definitions

def _failure(error):
    return str(error) if str(error).startswith('escrow.') else 'escrow.input_invalid'

def validate(request, *, invocation=None):

    def work(req, invocation):
        from stratbox.domains.cbr.tables.project_finance.validation import validate_flake
        invocation.stage('validate')
        try:
            return validate_flake(use_flake(req, invocation))
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return work(request, invocation)

def compare(request, *, invocation=None):

    def work(req, invocation):
        from stratbox.domains.cbr.tables.project_finance.validation import compare_flakes
        invocation.stage('compare')
        try:
            return compare_flakes(use_flake(req.before, invocation), use_flake(req.after, invocation))
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return work(request, invocation)

def readable(request, *, invocation=None):

    def work(req, invocation):
        from stratbox.domains.cbr.tables.project_finance.readable import readable_flake
        invocation.stage('readable')
        try:
            value = readable_flake(use_flake(req, invocation))
            invocation.budget.charge('output_bytes', len(value.data))
            invocation.record(value.identity)
            return value
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return work(request, invocation)

def align_observations(request, *, invocation=None):

    def work(req, invocation):
        from stratbox.domains.cbr.integration.project_finance.mapping import align_values
        invocation.stage('align')
        try:
            value = align_values(use_dataset(req.dataset, invocation), req.geography)
            invocation.use(value.lineage[-1])
            return value
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return work(request, invocation)


def capability_align_observations(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.align_observations', align_observations)


def capability_compare(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.compare', compare)


def capability_readable(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.readable', readable)


def capability_validate(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.validate', validate)
