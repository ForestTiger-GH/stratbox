"""Handlers for explicit validation, revision comparison and semantic mapping."""
from stratbox.core.execution import OperationFailure, run
from stratbox.domains.cbr.tables.project_finance.evidence import use_flake
from stratbox.domains.cbr.integration.project_finance.evidence import use_dataset
from . import definitions


def _failure(error):
    return str(error) if str(error).startswith("escrow.") else "escrow.input_invalid"


def validate(request, *, context=None):
    def work(req, invocation):
        from stratbox.domains.cbr.tables.project_finance.validation import validate_flake
        invocation.stage("validate")
        try:
            return validate_flake(use_flake(req, invocation))
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return run(definitions.VALIDATE, request, work, context=context)


def compare(request, *, context=None):
    def work(req, invocation):
        from stratbox.domains.cbr.tables.project_finance.validation import compare_flakes
        invocation.stage("compare")
        try:
            return compare_flakes(use_flake(req.before, invocation), use_flake(req.after, invocation))
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return run(definitions.COMPARE, request, work, context=context)


def readable(request, *, context=None):
    def work(req, invocation):
        from stratbox.domains.cbr.tables.project_finance.readable import readable_flake
        invocation.stage("readable")
        try:
            value = readable_flake(use_flake(req, invocation))
            invocation.budget.charge("output_bytes", len(value.data))
            invocation.record(value.identity)
            return value
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return run(definitions.READABLE, request, work, context=context)


def align_observations(request, *, context=None):
    def work(req, invocation):
        from stratbox.domains.cbr.integration.project_finance.mapping import align_values
        invocation.stage("align")
        try:
            value = align_values(use_dataset(req.dataset, invocation), req.geography)
            invocation.use(value.lineage[-1])
            return value
        except (TypeError, ValueError) as error:
            raise OperationFailure(_failure(error)) from None
    return run(definitions.ALIGN, request, work, context=context)
