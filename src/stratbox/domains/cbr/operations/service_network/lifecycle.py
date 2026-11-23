"""Independently callable service-network lifecycle boundaries."""
from dataclasses import asdict
from stratbox.core.execution import OperationFailure, run
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt
from .lifecycle_definitions import READABLE, HISTORY, RESTORE_HISTORY, ALIGN, CHANGES, VIEW, RENDER


def _call(definition,request,action,context):
    def work(req,invocation):
        try:
            return action(req,invocation)
        except (ValueError,TypeError,KeyError) as error:
            text=str(error)
            raise OperationFailure(text if text.startswith(("cbr.","request.","source.")) else "source.office_lifecycle_invalid") from None
    return run(definition,request,work,context=context)


def make_readable(request,*,context=None):
    from stratbox.domains.cbr.tables.service_network.readable import readable
    return _call(READABLE,request,readable,context)


def build_source_history(request,*,context=None):
    from stratbox.domains.cbr.tables.service_network.history import build_history
    def work(req,invocation):
        invocation.stage("source_history")
        result=build_history(req)
        for receipt in result.manifest.inputs:invocation.use(receipt)
        invocation.record(result.identity)
        return result
    return _call(HISTORY,request,work,context)


def restore_history(request,*,context=None):
    from stratbox.domains.cbr.tables.service_network.history import restore_history as decode
    def work(req,invocation):
        invocation.stage("restore_history")
        invocation.use(UsedInputReceipt("retained_history",req.identity,"application/vnd.stratbox.dataset+json","inline",req.manifest.dataset_id))
        for receipt in req.manifest.inputs:invocation.use(receipt)
        return decode(req)
    return _call(RESTORE_HISTORY,request,work,context)


def align_offices(request,*,context=None):
    from stratbox.domains.cbr.integration.service_network.alignment import align
    return _call(ALIGN,request,align,context)


def calculate_changes(request,*,context=None):
    from stratbox.domains.cbr.analytics.service_network.changes import calculate
    def work(req,invocation):
        invocation.stage("calculate_count_changes")
        result=calculate(req)
        for receipt in result.batch.lineage:invocation.use(receipt)
        invocation.record(ByteIdentity.of(canonical_manifest_bytes(asdict(result))))
        return result
    return _call(CHANGES,request,work,context)


def build_view(request,*,context=None):
    from stratbox.domains.cbr.products.service_network.views import build_view as prepare
    def work(req,invocation):
        invocation.stage("prepare_view")
        result=prepare(req)
        for receipt in result.manifest.inputs:invocation.use(receipt)
        invocation.record(result.identity)
        return result
    return _call(VIEW,request,work,context)


def render(request,*,context=None):
    from stratbox.domains.cbr.products.service_network.views import render_view
    def work(req,invocation):
        invocation.stage("render")
        invocation.use(UsedInputReceipt("prepared_office_view",req.view.identity,"application/vnd.stratbox.dataset+json","inline",req.view.manifest.dataset_id))
        return render_view(req,invocation.budget)
    return _call(RENDER,request,work,context)
