"""Thin operation wrappers; functional owners provide all domain behavior."""
from stratbox.core.execution import OperationFailure, run
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.tables.statistics.validation import validate_workbook_flake, compare_workbook_flakes
from stratbox.domains.cbr.tables.statistics.readable import readable_workbook
from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot, flake_from_snapshot
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot, dataset_from_snapshot
from stratbox.domains.cbr.analytics.statistics.changes import calculate_change as change_value, calculate_share as share_value
from stratbox.domains.cbr.products.statistics.views import build_view as view_value, view_snapshot, view_from_snapshot
from stratbox.domains.cbr.products.statistics.rendering import render_view as render_value
from . import definitions as D
from .evidence import use_value, record_value


def _run(definition, request, call, context):
    def work(req, invocation):
        invocation.stage(definition.operation_id.rsplit(".", 1)[-1])
        try:
            for port in definition.processing.inputs:
                value = req
                for name in port.path.split(".") if port.path else ():
                    value = getattr(value, name)
                use_value(value, invocation, port.name)
            value = call(req, invocation)
            record_value(value, req, definition, invocation)
        except (ValueError, TypeError) as error:
            code = str(error)
            raise OperationFailure(code if code.startswith(("cbr.", "workbook.", "dataset.", "observations."))
                                   else "cbr.statistics.input_invalid") from None
        return value
    return run(definition, request, work, context=context)


def extract(request, *, context=None):
    return _run(D.EXTRACT, request, lambda req, inv: extract_workbook_value(req.original, budget=inv.budget), context)


def validate(request, *, context=None):
    return _run(D.VALIDATE, request, lambda req, inv: validate_workbook_flake(req.flake), context)


def compare(request, *, context=None):
    return _run(D.COMPARE, request, lambda req, inv: compare_workbook_flakes(req.before, req.after), context)


def readable(request, *, context=None):
    return _run(D.READABLE, request, lambda req, inv: readable_workbook(req.flake), context)


def build_flake_snapshot(request, *, context=None):
    return _run(D.FLAKE_SNAPSHOT, request, lambda req, inv: flake_snapshot(req.flake), context)


def read_flake_snapshot(request, *, context=None):
    return _run(D.READ_FLAKE_SNAPSHOT, request, lambda req, inv: flake_from_snapshot(req.snapshot), context)


def align(request, *, context=None):
    return _run(D.ALIGN, request, lambda req, inv: align_statistics(req.flakes, row_bindings=req.row_bindings,
        period_bindings=req.period_bindings, mapping_version=req.mapping_version, strict=req.strict), context)


def calculate_change(request, *, context=None):
    return _run(D.CHANGE, request, lambda req, inv: change_value(req.dataset, req.before, req.after,
        method=req.method, release_ids=req.release_ids), context)


def calculate_share(request, *, context=None):
    return _run(D.SHARE, request, lambda req, inv: share_value(req.dataset, req.numerator_metric,
        req.denominator_metric, release_ids=req.release_ids), context)


def build_view(request, *, context=None):
    return _run(D.BUILD_VIEW, request, lambda req, inv: view_value(req.dataset, series_ids=req.series_ids,
        metric_ids=req.metric_ids, release_ids=req.release_ids, title=req.title), context)


def render_view(request, *, context=None):
    return _run(D.RENDER_VIEW, request, lambda req, inv: render_value(req.view, format=req.format), context)


def build_dataset_snapshot(request, *, context=None):
    return _run(D.DATASET_SNAPSHOT, request, lambda req, inv: dataset_snapshot(req.dataset), context)


def read_dataset_snapshot(request, *, context=None):
    return _run(D.READ_DATASET_SNAPSHOT, request, lambda req, inv: dataset_from_snapshot(req.snapshot), context)


def build_view_snapshot(request, *, context=None):
    return _run(D.VIEW_SNAPSHOT, request, lambda req, inv: view_snapshot(req.view), context)


def read_view_snapshot(request, *, context=None):
    return _run(D.READ_VIEW_SNAPSHOT, request, lambda req, inv: view_from_snapshot(req.snapshot), context)
