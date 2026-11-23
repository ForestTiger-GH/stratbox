"""Domain wrappers around independent observation, calculation and view stages."""
from dataclasses import asdict, is_dataclass

from stratbox.core.execution import OperationFailure, run
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.views import ObservationView, view_snapshot, view_from_snapshot, render_observation_view
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from ..integration.observations import integrate as integrate_rows
from ..analytics.snapshots import summary_snapshot as encode_summary, summary_from_snapshot
from ..products.views import prepare_view as prepare_headline_view
from . import pipeline_definitions as D
from .lineage import use_flake


def _identity(value):
    from ..documents.contracts import PublisherDocument
    if isinstance(value, PublisherDocument):
        from ..documents.snapshots import snapshot_document
        return snapshot_document(value).identity
    if isinstance(value, ObservationBatch):
        return observation_snapshot(value).identity
    if isinstance(value, ObservationView):
        return view_snapshot(value).identity
    if hasattr(value, "identity"):
        return value.identity
    return ByteIdentity.of(canonical_manifest_bytes(asdict(value)))


def _parameters(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return tuple(_parameters(item) for item in value)
    return value


def _execute(definition, request, build, *, context=None, with_invocation=False):
    def work(req, invocation):
        try:
            for name in ("snapshot", "batch", "view", "summary", "document", "payload"):
                if hasattr(req, name):
                    material = getattr(req, name)
                    identity = _identity(material)
                    invocation.use(UsedInputReceipt(name, identity, "application/json", "inline"))
                    size = identity.size + (sum(t.identity.size for _, t in material.tables)
                                            if isinstance(material, DatasetSnapshot) else 0)
                    invocation.budget.charge("input_bytes", size)
            if hasattr(req, "flake"):
                use_flake(invocation, req.flake)
            result = build(req, invocation) if with_invocation else build(req)
            identity = _identity(result)
            if isinstance(result, DatasetSnapshot):
                for name, table in result.tables:
                    invocation.account_output(table.identity, key="table:" + name)
            invocation.account_output(identity)
            invocation.record(identity, parameters={name: _parameters(getattr(req, name))
                for name in definition.processing.parameters})
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
