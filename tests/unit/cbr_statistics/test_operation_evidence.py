"""Public statistical wrappers pin semantic inputs and account complete outputs."""
from dataclasses import dataclass, replace
import json

import pytest

from stratbox.core.execution import ExecutionContext
from stratbox.core.limits import ExecutionBudget
from stratbox.domains.cbr.operations.statistics import contracts as C, handlers as operations
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot
from stratbox.domains.cbr.products.statistics.views import build_view
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.source_publications import SourceAssetIdentity

from test_workbook_replay import workbook


@dataclass(frozen=True)
class Boundary:
    handler: object
    request: object
    input_identities: tuple
    minimum_input_bytes: int
    output_snapshot: object = None


def snapshot_size(snapshot):
    """Logical manifest and all component payloads are separate byte obligations."""
    return snapshot.identity.size + sum(table.identity.size for _, table in snapshot.tables)


@pytest.fixture(scope="module")
def materials():
    series = "cbr.monetary_statistics.monetary_agg"
    original = IdentifiedOriginal(SourceAssetIdentity(series, "capture-1", "main"),
        SourcePayload(workbook(exact="123.00"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", series), "xlsx")
    source = extract_workbook_value(original)
    changed = extract_workbook_value(replace(original,
        payload=SourcePayload(workbook(exact="124.00"), original.payload.media_type, series)))
    source_snapshot = flake_snapshot(source)
    changed_snapshot = flake_snapshot(changed)
    dataset = align_statistics((source,))
    integrated_snapshot = dataset_snapshot(dataset)
    view = build_view(dataset)
    boundaries = {
        "extract": Boundary(operations.extract, C.ExtractWorkbookRequest(original),
                            (original.payload.identity,), original.payload.identity.size, source_snapshot),
        "align": Boundary(operations.align, C.AlignStatisticsRequest((source,)),
                          (source.identity,), snapshot_size(source_snapshot), integrated_snapshot),
        "read_flake": Boundary(operations.read_flake_snapshot, C.ReadSnapshotRequest(source_snapshot),
                               (source_snapshot.identity,), snapshot_size(source_snapshot), source_snapshot),
        "read_dataset": Boundary(operations.read_dataset_snapshot, C.ReadSnapshotRequest(integrated_snapshot),
                                 (integrated_snapshot.identity,), snapshot_size(integrated_snapshot), integrated_snapshot),
        "read_view": Boundary(operations.read_view_snapshot, C.ReadSnapshotRequest(view.snapshot),
                              (view.identity,), snapshot_size(view.snapshot), view.snapshot),
        "validate": Boundary(operations.validate, C.FlakeRequest(source),
                             (source.identity,), snapshot_size(source_snapshot)),
        "compare": Boundary(operations.compare, C.CompareWorkbooksRequest(source, changed),
                            (source.identity, changed.identity), snapshot_size(source_snapshot) + snapshot_size(changed_snapshot)),
    }
    return original, source, dataset, view, boundaries


def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    assert result.computation is not None
    assert result.computation.inputs == result.used_inputs
    return result


@pytest.mark.parametrize("name", ("extract", "align", "read_flake", "read_dataset", "read_view", "validate", "compare"))
def test_each_boundary_records_exact_inputs_output_identity_and_complete_payload_budget(materials, name):
    _, _, _, _, boundaries = materials
    case = boundaries[name]
    result = checked(case.handler(case.request))
    assert set(case.input_identities) <= {receipt.identity for receipt in result.used_inputs}
    usage = dict(result.resources_used)
    assert usage["input_bytes"] >= case.minimum_input_bytes
    assert usage["cells"] > 0
    if case.output_snapshot is not None:
        assert result.computation.output == result.value.identity
        assert usage["output_bytes"] >= snapshot_size(case.output_snapshot)
    else:
        # Validation and comparison have their own result identity, independent
        # of the material input hash or whether a representation was rendered.
        assert result.computation.output not in case.input_identities
        assert usage["output_bytes"] >= result.computation.output.size > 0
        repeated = checked(case.handler(case.request))
        assert repeated.computation.computation_id == result.computation.computation_id


def test_identical_bytes_under_different_asset_contexts_have_different_computation_evidence(materials):
    original, _, _, _, _ = materials
    other = replace(original, asset=replace(original.asset, asset_id="alternate_asset"))
    first = checked(operations.extract(C.ExtractWorkbookRequest(original)))
    second = checked(operations.extract(C.ExtractWorkbookRequest(other)))
    assert first.value.sheets == second.value.sheets
    assert original.payload.identity == other.payload.identity
    assert first.computation.computation_id != second.computation.computation_id
    first_parameters = json.loads(first.computation.version.manifest)["parameters"]
    second_parameters = json.loads(second.computation.version.manifest)["parameters"]
    assert (first_parameters, first.used_inputs) != (second_parameters, second.used_inputs)


def test_alignment_request_parameters_remain_in_computation_manifest(materials):
    _, source, _, _, _ = materials
    result = checked(operations.align(C.AlignStatisticsRequest((source,), mapping_version="test.mapping.v2", strict=False)))
    parameters = json.loads(result.computation.version.manifest)["parameters"]
    assert parameters["mapping_version"] == "test.mapping.v2"
    assert parameters["strict"] is False


@pytest.mark.parametrize("name,resource", (
    ("extract", "input_bytes"),
    ("align", "cells"),
    ("read_flake", "input_bytes"),
    ("read_dataset", "output_bytes"),
    ("read_view", "cells"),
    ("validate", "output_bytes"),
    ("compare", "input_bytes"),
))
def test_low_resource_budget_is_enforced_at_each_independent_boundary(materials, name, resource):
    _, _, _, _, boundaries = materials
    case = boundaries[name]
    if name == "extract":
        limit = case.minimum_input_bytes - 1
    elif name == "read_flake":
        # A manifest-only budget cannot admit all retained typed tables.
        limit = case.request.snapshot.identity.size
    elif name == "read_dataset":
        # Accounting only the output manifest would incorrectly pass this limit.
        limit = case.output_snapshot.identity.size
    else:
        limit = 1
    context = ExecutionContext(budget=ExecutionBudget(**{resource: limit}))
    result = case.handler(case.request, context=context)
    assert result.outcome == "failed", result.diagnostics
    assert any(item.code == "budget." + resource for item in result.diagnostics)
    assert result.value is None and result.effects == ()


def test_renderer_reads_only_prepared_view_and_enforces_output_budget(materials, monkeypatch):
    _, _, _, view, _ = materials
    def forbidden(*args, **kwargs):
        raise AssertionError("Rendering must not reacquire, extract, align or build a view")
    monkeypatch.setattr(operations, "extract_workbook_value", forbidden)
    monkeypatch.setattr(operations, "align_statistics", forbidden)
    monkeypatch.setattr(operations, "view_value", forbidden)
    monkeypatch.setattr("stratbox.domains.cbr.tables.statistics.extraction.read_workbook_cells", forbidden)
    request = C.RenderViewRequest(view, "csv")
    rendered = checked(operations.render_view(request))
    assert rendered.value.media_type == "text/csv" and rendered.value.data
    assert any(receipt.identity == view.identity for receipt in rendered.used_inputs)
    assert rendered.computation.output == rendered.value.identity
    parameters = json.loads(rendered.computation.version.manifest)["parameters"]
    assert parameters["format"] == "csv"
    limited = operations.render_view(request, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=len(rendered.value.data) - 1)))
    assert limited.outcome == "failed"
    assert limited.diagnostics[0].code == "budget.output_bytes"


def test_source_flake_snapshot_checks_cancellation_before_encoding_cells(materials):
    from stratbox.core.execution import OperationFailure
    _, value, _, _, _ = materials
    def checkpoint():
        raise OperationFailure("operation.cancelled", outcome="cancelled")
    with pytest.raises(OperationFailure, match="operation.cancelled"):
        flake_snapshot(value, checkpoint=checkpoint)
