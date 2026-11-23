"""Retain and reconstruct SORS source, restoration and crosswalk contexts."""
from __future__ import annotations
from dataclasses import replace

from stratbox.core.execution import OperationFailure, run
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsRestorationResult
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsCrosswalkResult
import stratbox.domains.cbr.analytics.corporate_lending.sors.snapshots as snapshots


def _use_context(value, invocation):
    from stratbox.domains.cbr.operations.corporate_lending.sors.api import _use_grids
    if isinstance(value, SorsSourceBundle):
        return _use_grids(invocation, value, "sors_source_bundle")
    if isinstance(value, SorsRestorationResult):
        result = _use_grids(invocation, value, "sors_restoration")
        if not isinstance(result.source_bundle, SorsSourceBundle):
            raise OperationFailure("sors.snapshot_context_required")
        return replace(result, source_bundle=_use_context(result.source_bundle, invocation))
    if isinstance(value, SorsCrosswalkResult):
        result = _use_grids(invocation, value, "sors_crosswalk")
        if not isinstance(result.strict_result, SorsRestorationResult):
            raise OperationFailure("sors.snapshot_context_required")
        return replace(result, strict_result=_use_context(result.strict_result, invocation))
    raise OperationFailure("sors.snapshot_kind_invalid")


def _code(error):
    text = str(error)
    return text if text.startswith(("sors.", "dataframe.")) and " " not in text else "sors.snapshot_invalid"


def _encode(definition, request, *, context=None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("encode_snapshot")
        value = _use_context(req.value, invocation)
        try:
            snapshot = snapshots.snapshot(value, dataset_id=req.dataset_id, version_id=req.version_id, checkpoint=invocation.check_cancelled)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        for name, table in snapshot.tables:
            invocation.account_output(table.identity, key=f"snapshot:{name}")
        invocation.account_output(snapshot.identity, key="snapshot:manifest")
        invocation.record(snapshot.identity, parameters={"dataset_id": snapshot.manifest.dataset_id, "version_id": snapshot.manifest.version_id})
        return snapshot
    return run(definition, request, work, context=context)


def _decode(definition, request, kind, *, context=None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("decode_snapshot")
        invocation.budget.charge("input_bytes", req.snapshot.identity.size + sum(table.identity.size for _, table in req.snapshot.tables))
        invocation.budget.charge("cells", sum(len(table.rows) * len(table.schema.columns) for _, table in req.snapshot.tables))
        invocation.use(UsedInputReceipt("snapshot", req.snapshot.identity, "application/json", "inline"))
        try:
            value = snapshots.from_snapshot(req.snapshot, expected_kind=kind, checkpoint=invocation.check_cancelled)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        invocation.parents.append(("stored_result", value.evidence))
        invocation.record(value.evidence.output, parameters={"snapshot": req.snapshot.identity.sha256, "profile": "sors-replay-context-1"})
        return value
    return run(definition, request, work, context=context)


def build_bundle_snapshot(request, *, context=None):
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import BUNDLE_SNAPSHOT
    return _encode(BUNDLE_SNAPSHOT, request, context=context)


def read_bundle_snapshot(request, *, context=None):
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import READ_BUNDLE_SNAPSHOT
    return _decode(READ_BUNDLE_SNAPSHOT, request, "bundle", context=context)


def build_restoration_snapshot(request, *, context=None):
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RESTORATION_SNAPSHOT
    return _encode(RESTORATION_SNAPSHOT, request, context=context)


def read_restoration_snapshot(request, *, context=None):
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import READ_RESTORATION_SNAPSHOT
    return _decode(READ_RESTORATION_SNAPSHOT, request, "restoration", context=context)


def build_crosswalk_snapshot(request, *, context=None):
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import CROSSWALK_SNAPSHOT
    return _encode(CROSSWALK_SNAPSHOT, request, context=context)


def read_crosswalk_snapshot(request, *, context=None):
    from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import READ_CROSSWALK_SNAPSHOT
    return _decode(READ_CROSSWALK_SNAPSHOT, request, "crosswalk", context=context)


def build_view_snapshot(request, *, context=None):
    from .definitions import VIEW_SNAPSHOT
    from .api import _use_views
    from stratbox.domains.cbr.products.corporate_lending.sors.snapshots import view_snapshot
    def work(req, invocation):
        invocation.stage("encode_snapshot")
        value = _use_views(req.value, invocation)
        try:
            snapshot = view_snapshot(value, dataset_id=req.dataset_id, version_id=req.version_id,
                                     checkpoint=invocation.check_cancelled)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        for name, table in snapshot.tables:
            invocation.account_output(table.identity, key="snapshot:" + name)
        invocation.account_output(snapshot.identity, key="snapshot:manifest")
        invocation.record(snapshot.identity)
        return snapshot
    return run(VIEW_SNAPSHOT, request, work, context=context)


def read_view_snapshot(request, *, context=None):
    from .definitions import READ_VIEW_SNAPSHOT
    from stratbox.domains.cbr.products.corporate_lending.sors.snapshots import view_from_snapshot
    def work(req, invocation):
        invocation.stage("decode_snapshot")
        invocation.budget.charge("input_bytes", req.snapshot.identity.size + sum(t.identity.size for _, t in req.snapshot.tables))
        invocation.budget.check("cells", sum(len(t.rows) * len(t.schema.columns) for _, t in req.snapshot.tables))
        invocation.use(UsedInputReceipt("snapshot", req.snapshot.identity, "application/json", "inline"))
        try:
            value = view_from_snapshot(req.snapshot, checkpoint=invocation.check_cancelled)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        invocation.parents.append(("prepared_views", value.evidence))
        invocation.record(value.evidence.output)
        return value
    return run(READ_VIEW_SNAPSHOT, request, work, context=context)
