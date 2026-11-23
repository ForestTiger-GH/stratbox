"""Domain wrappers around independent observation, calculation and view stages."""

from stratbox.core.execution import OperationFailure, run, values
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.views import ObservationView, view_snapshot, view_from_snapshot, render_observation_view
from ..integration.observations import integrate as integrate_rows
from ..analytics.snapshots import summary_snapshot as encode_summary, summary_from_snapshot
from ..products.views import prepare_view as prepare_headline_view
from . import pipeline_definitions as D
from .lineage import use_flake


def _snapshot(value, invocation):
    from ..documents.contracts import PublisherDocument
    if isinstance(value, PublisherDocument):
        from ..documents.snapshots import snapshot_document
        return snapshot_document(value)
    return None


def _execute(definition, request, build, *, context=None, with_invocation=False):
    def work(req, invocation):
        try:
            for name in ("snapshot", "batch", "view", "summary", "document", "payload"):
                if hasattr(req, name):
                    material = getattr(req, name)
                    values.use_value(material, invocation, name, snapshot_factory=_snapshot,
                                     charge_cells=False)
            if hasattr(req, "flake"):
                use_flake(invocation, req.flake)
            result = build(req, invocation) if with_invocation else build(req)
            values.record_value(result, req, definition, invocation, snapshot_factory=_snapshot,
                                table_prefix="table:", charge_cells=False)
            return result
        except (ValueError, TypeError, KeyError) as error:
            code = str(error)
            if not code.startswith(("minfin.", "observations.", "view.", "document.")) or len(code) > 95 or not all(c.isalnum() or c in "_." for c in code):
                code = "minfin.pipeline_invalid"
            raise OperationFailure(code) from None
    return run(definition, request, work, context=context)


def integrate(request, *, context=None):
    return _execute(D.INTEGRATE, request, integrate_rows, context=context)


def build_observation_snapshot(request, *, context=None):
    return _execute(D.OBSERVATION_SNAPSHOT, request, lambda r: observation_snapshot(r.batch, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_observations(request, *, context=None):
    return _execute(D.READ_OBSERVATIONS, request, lambda r: observations_from_snapshot(r.snapshot), context=context)


def build_summary_snapshot(request, *, context=None):
    return _execute(D.SUMMARY_SNAPSHOT, request, lambda r: encode_summary(r.summary, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_summary(request, *, context=None):
    return _execute(D.READ_SUMMARY, request, lambda r: summary_from_snapshot(r.snapshot), context=context)


def prepare_view(request, *, context=None):
    return _execute(D.PREPARE_VIEW, request, prepare_headline_view, context=context)


def build_view_snapshot(request, *, context=None):
    return _execute(D.VIEW_SNAPSHOT, request, lambda r: view_snapshot(r.view, dataset_id=r.dataset_id, version_id=r.version_id), context=context)


def read_view(request, *, context=None):
    return _execute(D.READ_VIEW, request, lambda r: view_from_snapshot(r.snapshot), context=context)


def render_view(request, *, context=None):
    return _execute(D.RENDER_VIEW, request, lambda r: render_observation_view(r.view, format=r.format), context=context)
