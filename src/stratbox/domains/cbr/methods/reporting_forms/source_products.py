"""Source-only reading and comparison remain independent of analytical coverage."""
from stratbox.core.execution import Completion, OperationFailure
from stratbox.domains.cbr.operations.reporting_forms.source_products_definitions import COMPARE, READABLE

def compare_sources(request, *, invocation=None):
    from stratbox.domains.cbr.tables.reporting_forms.comparison import compare

    def work(req, invocation):
        invocation.stage('compare_source_records')
        for value in (req.candidate, req.baseline):
            if value is not None:
                for receipt in value.lineage:
                    invocation.use(receipt)
        try:
            return compare(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return work(request, invocation)

def make_readable(request, *, invocation=None):
    from stratbox.domains.cbr.tables.reporting_forms.readable import readable

    def work(req, invocation):
        invocation.stage('readable_records')
        for receipt in req.lineage:
            invocation.use(receipt)
        try:
            result = readable(req, invocation)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
        if any((member.table is None for member in req.members)):
            return Completion(result, 'partial', 'source.form_readable_members_uncovered')
        return result
    return work(request, invocation)


def capability_compare_sources(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.compare', compare_sources)


def capability_make_readable(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.make_readable', make_readable)
