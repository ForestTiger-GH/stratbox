"""Runtime admission and independent operations for every report processing layer."""

from stratbox.core.execution import OperationFailure, run, values
from stratbox.core.formats.spreadsheets.extracts import extract_workbook
from stratbox.core.operations.source.validation import use_payload
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.workbooks import WorkbookExtract, workbook_snapshot, workbook_from_snapshot, readable_workbook, compare_workbooks
from stratbox.shared.data.views import ObservationView, prepare_observation_view, view_snapshot, view_from_snapshot, render_observation_view
from stratbox.shared.evidence import UsedInputReceipt
from ..publications.catalog import source
from ..tables.contracts import ExtractValidation, SemanticFlake
from ..tables.flakes import build_flake as interpret_flake, profile_identity
from ..tables.snapshots import flake_snapshot, flake_from_snapshot
from ..integration.observations import integrate as integrate_flake, align as align_batches, history
from ..analytics.revisions import calculate as calculate_revisions
from .handlers import _report
from . import pipeline_definitions as D


def _snapshot(value, invocation):
    if isinstance(value, SemanticFlake):
        return flake_snapshot(value)
    return None


def _execute(definition, request, build, *, context=None):
    def work(req, invocation):
        try:
            for name in ("extract", "flake", "snapshot", "batch", "view", "before", "after"):
                if hasattr(req, name):
                    material = getattr(req, name)
                    values.use_value(material, invocation, name, snapshot_factory=_snapshot,
                                     charge_cells=False)
            for index, batch in enumerate(getattr(req, "batches", ())):
                values.use_value(batch, invocation, f"integrated_release.{index}",
                                 snapshot_factory=_snapshot, charge_cells=False)
            if hasattr(req, "profile"):
                identity = profile_identity(req.profile)
                invocation.use(UsedInputReceipt("semantic_profile", identity, "application/json", "inline", req.profile.profile_id))
                invocation.budget.charge("input_bytes", identity.size)
            result = build(req, invocation)
            values.record_value(result, req, definition, invocation, snapshot_factory=_snapshot,
                                table_prefix="table:", charge_cells=False)
            return result
        except (ValueError, TypeError, KeyError) as error:
            code = str(error)
            if (not code.startswith(("frg.", "workbook.", "observations.", "view.", "calculation."))
                    or len(code) > 95 or not all(c.isalnum() or c in "_." for c in code)):
                code = "frg.pipeline.invalid"
            raise OperationFailure(code) from None
    return run(definition, request, work, context=context)


def _extract(req, invocation):
    _report(req.report)
    use_payload(req.report.payload, invocation, role="original", limit=64 * 1024 * 1024)
    value = extract_workbook(req.report.payload, series_id=req.report.source_id, issue_id=req.report.period.issue_id,
        profile_id="frg.workbook.cells", profile_version=1, budget=invocation.budget, checkpoint=invocation.check_cancelled)
    if value.format != req.report.format:
        raise ValueError("frg.extract.format_mismatch")
    return value


def extract(request, *, context=None):
    return _execute(D.EXTRACT, request, _extract, context=context)


def build_extract_snapshot(request, *, context=None):
    return _execute(D.EXTRACT_SNAPSHOT, request, lambda r, _: workbook_snapshot(r.extract, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def _read_extract(req, _):
    value = workbook_from_snapshot(req.snapshot)
    source(value.series_id)
    return value


def read_extract(request, *, context=None):
    return _execute(D.READ_EXTRACT, request, _read_extract, context=context)


def _validate(req, _):
    source(req.extract.series_id)
    req.extract.__post_init__()
    return ExtractValidation(req.extract.series_id, len(req.extract.sheets), sum(len(s.cells) for s in req.extract.sheets),
        sum(c.formula is not None and c.value is None for s in req.extract.sheets for c in s.cells), req.extract.qualifications)


def validate(request, *, context=None):
    return _execute(D.VALIDATE, request, _validate, context=context)


def compare(request, *, context=None):
    return _execute(D.COMPARE, request, lambda r, _: compare_workbooks(r.before, r.after), context=context)


def readable(request, *, context=None):
    return _execute(D.READABLE, request, lambda r, _: readable_workbook(r.extract), context=context)


def build_flake(request, *, context=None):
    return _execute(D.BUILD_FLAKE, request, lambda r, _: interpret_flake(r), context=context)


def build_flake_snapshot(request, *, context=None):
    return _execute(D.FLAKE_SNAPSHOT, request, lambda r, _: flake_snapshot(r.flake, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_flake(request, *, context=None):
    return _execute(D.READ_FLAKE, request, lambda r, _: flake_from_snapshot(r.snapshot), context=context)


def integrate(request, *, context=None):
    return _execute(D.INTEGRATE, request, lambda r, _: integrate_flake(r), context=context)


def align(request, *, context=None):
    return _execute(D.ALIGN, request, lambda r, _: align_batches(r), context=context)


def build_history(request, *, context=None):
    return _execute(D.HISTORY, request, lambda r, _: history(r), context=context)


def build_observation_snapshot(request, *, context=None):
    return _execute(D.OBSERVATION_SNAPSHOT, request, lambda r, _: observation_snapshot(r.batch, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_observations(request, *, context=None):
    return _execute(D.READ_OBSERVATIONS, request, lambda r, _: observations_from_snapshot(r.snapshot), context=context)


def calculate(request, *, context=None):
    return _execute(D.CALCULATE, request, lambda r, _: calculate_revisions(r), context=context)


def prepare_view(request, *, context=None):
    return _execute(D.PREPARE_VIEW, request, lambda r, _: prepare_observation_view(r.batch, view_id=r.view_id,
        metric_ids=r.metric_ids, period_kinds=r.period_kinds, subject_ids=r.subject_ids,
        qualifications=("supplied_profile_semantics", "no_implicit_aggregation")), context=context)


def build_view_snapshot(request, *, context=None):
    return _execute(D.VIEW_SNAPSHOT, request, lambda r, _: view_snapshot(r.view, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_view(request, *, context=None):
    return _execute(D.READ_VIEW, request, lambda r, _: view_from_snapshot(r.snapshot), context=context)


def render_view(request, *, context=None):
    return _execute(D.RENDER_VIEW, request, lambda r, _: render_observation_view(r.view, format=r.format), context=context)
