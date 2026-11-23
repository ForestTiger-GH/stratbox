"""Source-only reading and comparison remain independent of analytical coverage."""
from stratbox.core.execution import Completion,OperationFailure,run
from .source_products_definitions import COMPARE,READABLE


def compare_sources(request,*,context=None):
    from stratbox.domains.cbr.tables.reporting_forms.comparison import compare
    def work(req,invocation):
        invocation.stage("compare_source_records")
        for value in (req.candidate,req.baseline):
            if value is not None:
                for receipt in value.lineage:invocation.use(receipt)
        try:return compare(req)
        except ValueError as error:raise OperationFailure(str(error)) from None
    return run(COMPARE,request,work,context=context)


def make_readable(request,*,context=None):
    from stratbox.domains.cbr.tables.reporting_forms.readable import readable
    def work(req,invocation):
        invocation.stage("readable_records")
        for receipt in req.lineage:invocation.use(receipt)
        try:result=readable(req,invocation)
        except ValueError as error:raise OperationFailure(str(error)) from None
        if any(member.table is None for member in req.members):
            return Completion(result,"partial","source.form_readable_members_uncovered")
        return result
    return run(READABLE,request,work,context=context)
