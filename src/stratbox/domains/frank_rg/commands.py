"""Technical report commands executed inside the caller's admitted session.

Every entry point consumes the command's values and existing invocation. No
command creates an operation runner, session, transport or private pipeline.
"""
from __future__ import annotations

from importlib import import_module


def _symbol(reference):
    module, name = reference.split(":", 1)
    result = import_module(module)
    for part in name.split("."):
        result = getattr(result, part)
    return result


def _request(operation_id, values):
    from .capabilities import metadata, _REQUESTS
    document = metadata(operation_id)
    ports = document.get("processing", {}).get("inputs", ())
    direct = next((port for port in ports if port.get("path") == ""), None)
    if direct:
        request = values[direct["name"]]
        if not isinstance(request, _symbol(_REQUESTS[operation_id])):
            raise ValueError("frg.capability.request_type_mismatch")
        return request
    arguments = dict(values)
    for port in ports:
        path = port.get("path", port["name"])
        if "." in path:
            raise ValueError("frg.capability.nested_request_unsupported")
        if path != port["name"]:
            arguments[path] = arguments.pop(port["name"])
    return _symbol(_REQUESTS[operation_id])(**arguments)


def _project(operation_id, result):
    from .capabilities import metadata
    from stratbox.core.execution.runner import Completion
    value = result.value if isinstance(result, Completion) else result
    outputs = metadata(operation_id).get("processing", {}).get("outputs", ())
    projected = {}
    for output in outputs:
        item = value
        for part in output.get("path", output["name"]).split(".") if output.get("path", output["name"]) else ():
            item = item[part] if isinstance(item, dict) else getattr(item, part)
        projected[output["name"]] = item
    # The runtime's one-output convention accepts the raw value, whereas a
    # multi-output command returns its named group atomically.
    answer = next(iter(projected.values())) if len(projected) == 1 else projected
    if isinstance(result, Completion):
        return Completion(answer, result.outcome, *result.diagnostics)
    return answer


def _source(name, values, invocation):
    from .operations import handlers
    return _project("frg." + name, getattr(handlers, "_work_" + name)(
        _request("frg." + name, values), invocation))


def _housekeeping(name, values, invocation):
    from .operations import housekeeping
    return _project("frg." + name, getattr(housekeeping, "_work_" + name)(
        _request("frg." + name, values), invocation))


def _pipeline(name, values, invocation):
    from stratbox.core.execution import values as accepted_values
    from stratbox.core.execution.contracts import OperationFailure
    from stratbox.operations.declarations import definition
    from .operations.pipeline_handlers import _snapshot
    operation_id = "frg." + name
    request = _request(operation_id, values)
    try:
        for field in ("extract", "flake", "snapshot", "batch", "view", "before", "after"):
            if hasattr(request, field):
                accepted_values.use_value(getattr(request, field), invocation, field,
                    snapshot_factory=_snapshot, charge_cells=False)
        for index, batch in enumerate(getattr(request, "batches", ())):
            accepted_values.use_value(batch, invocation, f"integrated_release.{index}",
                snapshot_factory=_snapshot, charge_cells=False)
        if hasattr(request, "profile"):
            from .tables.flakes import profile_identity
            from stratbox.shared.evidence import UsedInputReceipt
            identity = profile_identity(request.profile)
            invocation.use(UsedInputReceipt("semantic_profile", identity, "application/json", "inline", request.profile.profile_id))
            invocation.budget.charge("input_bytes", identity.size)
        result = _build(name, request, invocation)
        accepted_values.record_value(result, request, definition(operation_id), invocation,
            snapshot_factory=_snapshot, table_prefix="table:", charge_cells=False)
        return _project(operation_id, result)
    except (ValueError, TypeError, KeyError) as error:
        code = str(error)
        if (not code.startswith(("frg.", "workbook.", "observations.", "view.", "calculation."))
                or len(code) > 95 or not all(char.isalnum() or char in "_." for char in code)):
            code = "frg.pipeline.invalid"
        raise OperationFailure(code) from None


def _build(name, request, invocation):
    """Dispatch technical algorithms within this publisher's owned namespace."""
    from .operations.pipeline_handlers import _extract, _read_extract, _validate
    from stratbox.shared.data.workbooks import workbook_snapshot, readable_workbook, compare_workbooks
    from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
    from stratbox.shared.data.views import prepare_observation_view, view_snapshot, view_from_snapshot, render_observation_view
    from .tables.flakes import build_flake
    from .tables.snapshots import flake_snapshot, flake_from_snapshot
    from .integration.observations import integrate, align, history
    from .analytics.revisions import calculate
    functions = {
        "extract": lambda: _extract(request, invocation),
        "extract_snapshot": lambda: workbook_snapshot(request.extract, dataset_id=request.dataset_id, version_id=request.version_id),
        "read_extract": lambda: _read_extract(request, invocation),
        "validate": lambda: _validate(request, invocation),
        "compare": lambda: compare_workbooks(request.before, request.after),
        "readable": lambda: readable_workbook(request.extract),
        "build_flake": lambda: build_flake(request),
        "flake_snapshot": lambda: flake_snapshot(request.flake, dataset_id=request.dataset_id, version_id=request.version_id),
        "read_flake": lambda: flake_from_snapshot(request.snapshot),
        "integrate": lambda: integrate(request),
        "align": lambda: align(request),
        "build_history": lambda: history(request),
        "observation_snapshot": lambda: observation_snapshot(request.batch, dataset_id=request.dataset_id, version_id=request.version_id),
        "read_observations": lambda: observations_from_snapshot(request.snapshot),
        "calculate": lambda: calculate(request),
        "prepare_view": lambda: prepare_observation_view(request.batch, view_id=request.view_id,
            metric_ids=request.metric_ids, period_kinds=request.period_kinds, subject_ids=request.subject_ids,
            qualifications=("supplied_profile_semantics", "no_implicit_aggregation")),
        "view_snapshot": lambda: view_snapshot(request.view, dataset_id=request.dataset_id, version_id=request.version_id),
        "read_view": lambda: view_from_snapshot(request.snapshot),
        "render_view": lambda: render_observation_view(request.view, format=request.format),
    }
    return functions[name]()


def compose_catalog(values, invocation):
    from .publications.contracts import Catalog
    return Catalog(values["inventory"], values["selections"])


def bind_reviewed_layout(values, invocation):
    from .tables.layouts import bind_layout
    from stratbox.shared.evidence import UsedInputReceipt
    layout = values["layout"]
    result = bind_layout(values["extract"], layout, periods=values["periods"])
    invocation.use(UsedInputReceipt("semantic_layout", layout.identity, "application/json", "inline", layout.profile_id))
    for identity in layout.reviewed_originals:
        invocation.use(UsedInputReceipt("layout_review_original", identity, "application/octet-stream", "reference_only", layout.source_id))
    return result



def discover(values, invocation):
    return _source("discover", values, invocation)


def inspect(values, invocation):
    return _source("inspect", values, invocation)


def select(values, invocation):
    return _source("select", values, invocation)


def acquire(values, invocation):
    return _source("acquire", values, invocation)


def capture(values, invocation):
    return _source("capture", values, invocation)


def prepare_file(values, invocation):
    return _source("prepare_file", values, invocation)


def plan_updates(values, invocation):
    return _source("plan_updates", values, invocation)


def assess_material(values, invocation):
    return _source("assess_material", values, invocation)


def plan_cleanup(values, invocation):
    return _housekeeping("plan_cleanup", values, invocation)


def apply_cleanup(values, invocation):
    return _housekeeping("apply_cleanup", values, invocation)


def prepare_archive(values, invocation):
    return _housekeeping("prepare_archive", values, invocation)


def prepare_archive_to_store(values, invocation):
    return _housekeeping("prepare_archive_to_store", values, invocation)


def extract(values, invocation):
    return _pipeline("extract", values, invocation)


def extract_snapshot(values, invocation):
    return _pipeline("extract_snapshot", values, invocation)


def read_extract(values, invocation):
    return _pipeline("read_extract", values, invocation)


def validate(values, invocation):
    return _pipeline("validate", values, invocation)


def compare(values, invocation):
    return _pipeline("compare", values, invocation)


def readable(values, invocation):
    return _pipeline("readable", values, invocation)


def build_flake(values, invocation):
    return _pipeline("build_flake", values, invocation)


def flake_snapshot(values, invocation):
    return _pipeline("flake_snapshot", values, invocation)


def read_flake(values, invocation):
    return _pipeline("read_flake", values, invocation)


def integrate(values, invocation):
    return _pipeline("integrate", values, invocation)


def align(values, invocation):
    return _pipeline("align", values, invocation)


def build_history(values, invocation):
    return _pipeline("build_history", values, invocation)


def observation_snapshot(values, invocation):
    return _pipeline("observation_snapshot", values, invocation)


def read_observations(values, invocation):
    return _pipeline("read_observations", values, invocation)


def calculate(values, invocation):
    return _pipeline("calculate", values, invocation)


def prepare_view(values, invocation):
    return _pipeline("prepare_view", values, invocation)


def view_snapshot(values, invocation):
    return _pipeline("view_snapshot", values, invocation)


def read_view(values, invocation):
    return _pipeline("read_view", values, invocation)


def render_view(values, invocation):
    return _pipeline("render_view", values, invocation)
