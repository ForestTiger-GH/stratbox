"""Independent neutral processing handlers; each call returns a value, not a save."""
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
import json

from stratbox.core.execution import OperationFailure, run
from stratbox.shared.data import workbooks as W, documents as D, views as V
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data import observation_snapshots as O
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from . import definitions as C


def _control_value(value):
    """Canonical control/output metadata without fixed-point scalar expansion."""
    if isinstance(value, Enum):
        return value.value
    if value is None or type(value) in {bool, int, str}:
        return value
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if type(value) in {date, datetime, time}:
        return {type(value).__name__: value.isoformat()}
    if isinstance(value, timedelta):
        return {"microseconds": (value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds}
    if isinstance(value, ByteIdentity):
        return {"sha256": value.sha256, "size": value.size}
    if isinstance(value, (tuple, list)):
        return [_control_value(v) for v in value]
    if is_dataclass(value):
        return {f.name: _control_value(getattr(value, f.name)) for f in fields(value)}
    raise ValueError("processing.control_value_unsupported")


def _snapshot(value):
    if isinstance(value, DatasetSnapshot):
        return value
    if isinstance(value, W.WorkbookExtract):
        return W.workbook_snapshot(value)
    if isinstance(value, D.DocumentExtract):
        return D.document_snapshot(value)
    if isinstance(value, V.ObservationView):
        return V.view_snapshot(value)
    if isinstance(value, ObservationBatch):
        return observation_snapshot(value)
    return None


def _preflight_input(value, invocation):
    """Check retained shapes and a bounded byte floor before any encoding.

    Repeated references count on every occurrence, as they do in a snapshot.
    This admission estimate never charges resources: the actual manifest and
    table identities below remain the authoritative byte and cell accounting.
    """
    invocation.check_cancelled()
    if isinstance(value, DatasetSnapshot):
        size, cells = value.identity.size, 0
        for _, table in value.tables:
            invocation.check_cancelled()
            size += table.identity.size
            cells += len(table.rows) * max(1, len(table.schema.columns))
            invocation.budget.check("input_bytes", size)
            invocation.budget.check("cells", cells)
        invocation.budget.check("input_bytes", size)
        return
    if isinstance(value, W.WorkbookExtract):
        cells = len(W._META.columns)
        for sheet in value.sheets:
            invocation.check_cancelled()
            cells += len(W._SHEETS.columns) + len(sheet.cells) * len(W._CELLS.columns)
            invocation.budget.check("cells", cells)
    elif isinstance(value, D.DocumentExtract):
        cells = len(D._META.columns) + len(value.blocks) * len(D._BLOCKS.columns)
    elif isinstance(value, (ObservationBatch, V.ObservationView)):
        batch = value.batch if isinstance(value, V.ObservationView) else value
        cells = len(O._METADATA.columns) + len(batch.observations) * len(O._OBSERVATIONS.columns)
        if isinstance(value, V.ObservationView):
            cells += len(V._SCHEMA.columns)
    else:
        return
    invocation.budget.check("cells", cells)
    size = 0

    def visit(item, depth=0):
        nonlocal size
        invocation.check_cancelled()
        if depth > 32:
            raise ValueError("processing.input_structure_invalid")
        if isinstance(item, str):
            # First use the allocation-free character floor. Escaping/UTF-8
            # then needs only a bounded temporary chunk, even for one huge cell.
            size += len(item) + 2
            invocation.budget.check("input_bytes", size)
            for start in range(0, len(item), 4096):
                invocation.check_cancelled()
                chunk = item[start:start + 4096]
                size += len(json.dumps(chunk, ensure_ascii=False).encode("utf-8")) - 2 - len(chunk)
                invocation.budget.check("input_bytes", size)
        elif isinstance(item, (tuple, list)):
            size += 2
            invocation.budget.check("input_bytes", size)
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, Decimal):
            # Coefficient digits are a floor for both the source-preserving
            # scientific token and the bounded fixed-point manifest codec.
            size += len(item.as_tuple().digits)
            invocation.budget.check("input_bytes", size)
        elif type(item) is int:
            # Do not turn a caller-owned large integer into an unbounded token.
            size += max(1, (item.bit_length() - 1) * 30102 // 100000 + 1) + (item < 0)
            invocation.budget.check("input_bytes", size)
        elif isinstance(item, (date, time, timedelta, bool)) or item is None:
            size += 1
            invocation.budget.check("input_bytes", size)
        elif is_dataclass(item):
            for field in fields(item):
                visit(getattr(item, field.name), depth + 1)

    visit(value)
    invocation.check_cancelled()


def _pin_inputs(request, invocation):
    for field in fields(request):
        value = getattr(request, field.name)
        _preflight_input(value, invocation)
        snapshot = _snapshot(value)
        if snapshot is None:
            continue
        invocation.use(UsedInputReceipt("input_"+field.name, snapshot.identity,
            "application/vnd.stratbox.dataset+json", "inline", snapshot.manifest.dataset_id,
            version=snapshot.identity))
        for receipt in snapshot.manifest.inputs:
            invocation.use(receipt)
        invocation.budget.charge("input_bytes", snapshot.identity.size)
        for _, table in snapshot.tables:
            invocation.check_cancelled()
            invocation.budget.charge("input_bytes", table.identity.size)
            invocation.budget.charge("cells", len(table.rows) * max(1, len(table.schema.columns)))


def _run(definition, request, work, context):
    def execute(req, invocation):
        invocation.stage("process")
        try:
            _pin_inputs(req, invocation)
            parameters = {name: _control_value(getattr(req, name)) for name in definition.processing.parameters}
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
        if identity is None:
            identity = ByteIdentity.of(canonical_manifest_bytes(_control_value(value)))
        invocation.account_output(identity, key="result")
        invocation.record(identity, parameters=parameters)
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
