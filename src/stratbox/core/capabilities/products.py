"""Independent view preparation and bounded representation encoding."""
from typing import Mapping
from dataclasses import replace

from stratbox.core.execution.contracts import OperationFailure
from stratbox.shared.data.views import ObservationView, prepare_observation_view, render_observation_view
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.assessment import value_evidence


def view_prepare(request: Mapping, invocation):
    value = request["observations"]
    if not isinstance(value, ObservationBatch):
        raise OperationFailure("view.observations_required")
    return prepare_observation_view(value, view_id=(request.get("view_id") or value.dataset_id + ".view"),
        metric_ids=tuple(request.get("metric_ids", ())), subject_ids=tuple(request.get("subject_ids", ())))


def representation_encode(request: Mapping, invocation):
    value = request["view"]
    if not isinstance(value, ObservationView):
        raise OperationFailure("render.view_required")
    representation = render_observation_view(value, format=request.get("format", "csv"))
    if len(representation.data) > request.get("max_bytes", 32 * 1024 * 1024):
        raise OperationFailure("render.size_limit")
    invocation.account_output(representation.identity)
    evidence = value_evidence(value)
    admitted = dict(getattr(invocation.context, "binding_identities", ()))
    methods = tuple(sorted({*evidence.method_fingerprints, *(fingerprint for key, fingerprint in admitted.items()
        if key == "method" or key.startswith(("method:", "implementation:")))}))
    return replace(representation, evidence=replace(evidence,
        qualifications=evidence.qualifications | {"representation.encoded"}, method_fingerprints=methods))
