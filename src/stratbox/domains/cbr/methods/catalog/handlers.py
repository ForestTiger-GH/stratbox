"""Read-only domain catalog handlers; no acquisition or processing is executed."""
from stratbox.core.execution import OperationFailure
from stratbox.domains.cbr.operations.catalog.definitions import DESCRIBE_SOURCE, DESCRIBE_FAMILY

def describe_source(request, *, invocation=None):

    def work(req, invocation):
        from stratbox.domains.cbr.operations.bindings import bind_source
        invocation.stage('describe_source')
        try:
            return bind_source(req.series_id, format=req.format, table_id=req.table_id, edition=req.edition)
        except ValueError as error:
            code = str(error)
            raise OperationFailure(code if code.startswith('cbr.') else 'cbr.catalog.binding_invalid') from None
    return work(request, invocation)

def describe_family(request, *, invocation=None):

    def work(req, invocation):
        from stratbox.domains.cbr.operations.bindings import bind_family
        invocation.stage('describe_family')
        try:
            return bind_family(req.family_id)
        except ValueError as error:
            code = str(error)
            raise OperationFailure(code if code.startswith('cbr.') else 'cbr.catalog.binding_invalid') from None
    return work(request, invocation)


def capability_describe_family(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.describe_family', describe_family)


def capability_describe_source(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.describe_source', describe_source)
