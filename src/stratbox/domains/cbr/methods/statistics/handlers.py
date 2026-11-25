"""Thin operation wrappers; functional owners provide all domain behavior."""
from stratbox.core.execution import OperationFailure
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.tables.statistics.validation import validate_workbook_flake, compare_workbook_flakes
from stratbox.domains.cbr.tables.statistics.readable import readable_workbook
from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot, flake_from_snapshot
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot, dataset_from_snapshot
from stratbox.domains.cbr.analytics.statistics.changes import calculate_change as change_value, calculate_share as share_value
from stratbox.domains.cbr.products.statistics.views import build_view as view_value, view_snapshot, view_from_snapshot
from stratbox.domains.cbr.products.statistics.rendering import render_view as render_value
from stratbox.domains.cbr.operations.statistics import definitions as D
from stratbox.domains.cbr.operations.statistics.evidence import use_value, record_value

def _run(definition, request, call, invocation):

    def work(req, invocation):
        invocation.stage(definition.operation_id.rsplit('.', 1)[-1])
        try:
            for port in definition.processing.inputs:
                value = req
                for name in port.path.split('.') if port.path else ():
                    value = getattr(value, name)
                use_value(value, invocation, port.name)
            value = call(req, invocation)
            record_value(value, req, definition, invocation)
        except (ValueError, TypeError) as error:
            code = str(error)
            raise OperationFailure(code if code.startswith(('cbr.', 'workbook.', 'dataset.', 'observations.')) else 'cbr.statistics.input_invalid') from None
        return value
    return work(request, invocation)

def extract(request, *, invocation=None):
    return _run(D.EXTRACT, request, lambda req, inv: extract_workbook_value(req.original, budget=inv.budget), invocation)

def validate(request, *, invocation=None):
    return _run(D.VALIDATE, request, lambda req, inv: validate_workbook_flake(req.flake), invocation)

def compare(request, *, invocation=None):
    return _run(D.COMPARE, request, lambda req, inv: compare_workbook_flakes(req.before, req.after), invocation)

def readable(request, *, invocation=None):
    return _run(D.READABLE, request, lambda req, inv: readable_workbook(req.flake), invocation)

def build_flake_snapshot(request, *, invocation=None):
    return _run(D.FLAKE_SNAPSHOT, request, lambda req, inv: flake_snapshot(req.flake), invocation)

def read_flake_snapshot(request, *, invocation=None):
    return _run(D.READ_FLAKE_SNAPSHOT, request, lambda req, inv: flake_from_snapshot(req.snapshot), invocation)

def align(request, *, invocation=None):
    return _run(D.ALIGN, request, lambda req, inv: align_statistics(req.flakes, row_bindings=req.row_bindings, period_bindings=req.period_bindings, mapping_version=req.mapping_version, strict=req.strict), invocation)

def calculate_change(request, *, invocation=None):
    return _run(D.CHANGE, request, lambda req, inv: change_value(req.dataset, req.before, req.after, method=req.method, release_ids=req.release_ids), invocation)

def calculate_share(request, *, invocation=None):
    return _run(D.SHARE, request, lambda req, inv: share_value(req.dataset, req.numerator_metric, req.denominator_metric, release_ids=req.release_ids), invocation)

def build_view(request, *, invocation=None):
    return _run(D.BUILD_VIEW, request, lambda req, inv: view_value(req.dataset, series_ids=req.series_ids, metric_ids=req.metric_ids, release_ids=req.release_ids, title=req.title), invocation)

def render_view(request, *, invocation=None):
    return _run(D.RENDER_VIEW, request, lambda req, inv: render_value(req.view, format=req.format), invocation)

def build_dataset_snapshot(request, *, invocation=None):
    return _run(D.DATASET_SNAPSHOT, request, lambda req, inv: dataset_snapshot(req.dataset), invocation)

def read_dataset_snapshot(request, *, invocation=None):
    return _run(D.READ_DATASET_SNAPSHOT, request, lambda req, inv: dataset_from_snapshot(req.snapshot), invocation)

def build_view_snapshot(request, *, invocation=None):
    return _run(D.VIEW_SNAPSHOT, request, lambda req, inv: view_snapshot(req.view), invocation)

def read_view_snapshot(request, *, invocation=None):
    return _run(D.READ_VIEW_SNAPSHOT, request, lambda req, inv: view_from_snapshot(req.snapshot), invocation)


def capability_align(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.align', align)


def capability_build_view(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.build_view', build_view)


def capability_calculate_change(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.calculate_change', calculate_change)


def capability_calculate_share(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.calculate_share', calculate_share)


def capability_build_dataset_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.dataset_snapshot', build_dataset_snapshot)


def capability_read_dataset_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.read_dataset_snapshot', read_dataset_snapshot)


def capability_read_view_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.read_view_snapshot', read_view_snapshot)


def capability_render_view(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.render_view', render_view)


def capability_build_view_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.statistics.view_snapshot', build_view_snapshot)


def capability_compare(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.tables.compare', compare)


def capability_extract(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.tables.extract', extract)


def capability_build_flake_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.tables.flake_snapshot', build_flake_snapshot)


def capability_read_flake_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.tables.read_flake_snapshot', read_flake_snapshot)


def capability_readable(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.tables.readable', readable)


def capability_validate(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.tables.validate', validate)
