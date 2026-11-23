"""Independent neutral processing handlers; each call returns a value, not a save."""
from stratbox.core.execution import OperationFailure, run
from stratbox.shared.data import workbooks as W, documents as D, views as V
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import UsedInputReceipt
from . import definitions as C


def _run(definition, request, work, context):
    def execute(req, invocation):
        invocation.stage("process")
        try:
            value = work(req, invocation)
        except (ValueError, TypeError, KeyError) as error:
            code = str(error)
            if not code or any(not(c.isalnum() or c in "._") for c in code):
                code = "processing.input_invalid"
            raise OperationFailure(code) from None
        if isinstance(value, DatasetSnapshot):
            for receipt in value.manifest.inputs:
                invocation.use(receipt)
            for name, table in value.tables:
                invocation.account_output(table.identity, key=name)
        else:
            for receipt in getattr(value, "lineage", ()):
                invocation.use(receipt)
        identity = getattr(value, "identity", None)
        if identity is not None:
            invocation.account_output(identity, key="result")
            invocation.record(identity)
        return value
    return run(definition, request, execute, context=context)


def extract_workbook(request, *, context=None):
    from stratbox.core.formats.spreadsheets.extracts import extract_workbook as extract
    def work(req, inv):
        inv.use(UsedInputReceipt.for_payload(req.payload, "source"))
        inv.budget.charge("input_bytes", len(req.payload.data))
        return extract(req.payload, series_id=req.series_id, issue_id=req.issue_id, asset_id=req.asset_id,
                       budget=inv.budget, checkpoint=inv.check_cancelled)
    return _run(C.WORKBOOK, request, work, context)


def readable_workbook(request, *, context=None):
    return _run(C.WORKBOOK_READABLE, request, lambda r, i: W.readable_workbook(r.workbook), context)


def snapshot_workbook(request, *, context=None):
    return _run(C.WORKBOOK_SNAPSHOT, request, lambda r, i: W.workbook_snapshot(r.workbook), context)


def replay_workbook(request, *, context=None):
    return _run(C.WORKBOOK_REPLAY, request, lambda r, i: W.workbook_from_snapshot(r.snapshot), context)


def compare_workbooks(request, *, context=None):
    return _run(C.WORKBOOK_COMPARE, request, lambda r, i: W.compare_workbooks(r.before, r.after), context)


def extract_document(request, *, context=None):
    from stratbox.core.formats.documents import extract_document as extract
    def work(req, inv):
        inv.use(UsedInputReceipt.for_payload(req.payload, "source"))
        inv.budget.charge("input_bytes", len(req.payload.data))
        return extract(req.payload, series_id=req.series_id, issue_id=req.issue_id, asset_id=req.asset_id,
                       budget=inv.budget, checkpoint=inv.check_cancelled)
    return _run(C.DOCUMENT, request, work, context)


def readable_document(request, *, context=None):
    return _run(C.DOCUMENT_READABLE, request, lambda r, i: D.readable_document(r.document), context)


def snapshot_document(request, *, context=None):
    return _run(C.DOCUMENT_SNAPSHOT, request, lambda r, i: D.document_snapshot(r.document), context)


def replay_document(request, *, context=None):
    return _run(C.DOCUMENT_REPLAY, request, lambda r, i: D.document_from_snapshot(r.snapshot), context)


def prepare_view(request, *, context=None):
    return _run(C.VIEW, request, lambda r, i: V.prepare_observation_view(r.batch, view_id=r.view_id,
        metric_ids=r.metric_ids, period_kinds=r.period_kinds, subject_ids=r.subject_ids,
        coverage=r.coverage, qualifications=r.qualifications), context)


def snapshot_view(request, *, context=None):
    return _run(C.VIEW_SNAPSHOT, request, lambda r, i: V.view_snapshot(r.view), context)


def replay_view(request, *, context=None):
    return _run(C.VIEW_REPLAY, request, lambda r, i: V.view_from_snapshot(r.snapshot), context)


def render_view(request, *, context=None):
    return _run(C.VIEW_RENDER, request, lambda r, i: V.render_observation_view(r.view, format=r.format), context)


def plan_update(request, *, context=None):
    from stratbox.shared.data.updates import plan_updates
    return _run(C.UPDATE, request, lambda r, i: plan_updates(r.targets, r.retained, coverage=r.coverage), context)
