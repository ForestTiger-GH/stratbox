"""Read-only domain catalog handlers; no acquisition or processing is executed."""
from stratbox.core.execution import OperationFailure, run
from .definitions import DESCRIBE_SOURCE, DESCRIBE_FAMILY


def describe_source(request, *, context=None):
    def work(req, invocation):
        from stratbox.domains.cbr.operations.bindings import bind_source
        invocation.stage("describe_source")
        try:
            return bind_source(req.series_id, format=req.format, table_id=req.table_id, edition=req.edition)
        except ValueError as error:
            code = str(error)
            raise OperationFailure(code if code.startswith("cbr.") else "cbr.catalog.binding_invalid") from None
    return run(DESCRIBE_SOURCE, request, work, context=context)


def describe_family(request, *, context=None):
    def work(req, invocation):
        from stratbox.domains.cbr.operations.bindings import bind_family
        invocation.stage("describe_family")
        try:
            return bind_family(req.family_id)
        except ValueError as error:
            code = str(error)
            raise OperationFailure(code if code.startswith("cbr.") else "cbr.catalog.binding_invalid") from None
    return run(DESCRIBE_FAMILY, request, work, context=context)
