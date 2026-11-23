"""The Minfin flake and its calculations stay the same across dataset adapters."""
from dataclasses import replace

import pytest

from stratbox.core.execution import ExecutionContext
from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution.handoff import bind_request, project_output
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.datasets.memory import MemoryDatasetStore
from stratbox.core.storage.datasets.codec import reference_from, reference_value
from stratbox.core.storage.datasets import operations as datasets
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.minfin import (
    FlakeSnapshotRequest, ReadFlakeSnapshotRequest, SummaryRequest,
    build_flake_snapshot, calculate_headlines, read_flake_snapshot,
)
from stratbox.domains.minfin.tables.contracts import FlakeColumn, FlakeRow, FlakeTable
from stratbox.domains.minfin.operations import definitions as D


def _flake(kind):
    columns = (FlakeColumn(3, "October 2025", "2025-10"), FlakeColumn(6, "October 2026", "2026-10"))
    if kind == "budget":
        return FlakeTable("minfin.fedbud", "minfin.fedbud.annex3.monthly", ByteIdentity.of(b"original"),
            "Source", "monthly", "ytd", columns, (
                FlakeRow(3, "1", "Доходы, всего", ("100.0000", "110")),
                FlakeRow(5, "2", "Расходы, всего", ("120", "135")),
                FlakeRow(8, "3", "Дефицит (-)/Профицит (+)", ("-20", "-25")),
                FlakeRow(9, "4", "No numeric coercion", (None, "")),
            ), "minfin.flake.budget.v2", "billion_rub")
    return FlakeTable("minfin.nwf", "minfin.nwf.flows", ByteIdentity.of(b"nwf original"),
        "Source", "monthly", "stock", columns, (
            FlakeRow(5, "2", "Объем на конец периода", ("100.0000", "110"), "RUB", "1000000000", "stock"),
            FlakeRow(8, "5", "Размещено в иные разрешенные активы на конец периода", ("20", "30"), "RUB", "1000000000", "stock"),
            FlakeRow(9, "6", "Other source units", (None, "")),
        ), "minfin.flake.nwf.v2", "mixed")


def _assert(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result


@pytest.mark.parametrize("kind", ("budget", "nwf"))
def test_same_flake_snapshot_and_calculation_in_memory_and_file_backends(tmp_path, kind):
    flake = _flake(kind)
    encoded = _assert(build_flake_snapshot(FlakeSnapshotRequest(flake, flake.source_id, "edition-1")))
    assert encoded.value.manifest.coverage.status == "unknown"
    memory = MemoryDatasetStore(provider_id="memory", scope_id="application")
    files = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="shared")
    context = ExecutionContext(bindings=tuple(
        ProviderBinding(provider.provider_id, CapabilityRequirement(role), "ready", provider, provider.scope_id)
        for provider in (memory, files) for role in ("dataset_writer", "dataset_reader", "dataset_catalog")
    ))
    references = []
    for provider in (memory, files):
        written = _assert(bind_request(datasets.WRITE, {"snapshot": project_output(encoded, "dataset")},
            parameters={"selection": ProviderSelection(provider.provider_id, provider.scope_id)})
            .invoke(datasets.write_snapshot, context=context))
        references.append(written.value.reference)
        read = _assert(bind_request(datasets.READ, {"reference": project_output(written, "reference")})
                       .invoke(datasets.read_snapshot, context=context))
        restored = _assert(bind_request(D.READ_FLAKE_SNAPSHOT, {"snapshot": project_output(read, "snapshot")})
                           .invoke(read_flake_snapshot))
        assert restored.value == flake
        assert restored.computation.parents
        direct = _assert(calculate_headlines(SummaryRequest(flake)))
        retained = _assert(calculate_headlines(SummaryRequest(restored.value)))
        assert direct.value == retained.value
        assert direct.computation.computation_id == retained.computation.computation_id
        listed = _assert(datasets.list_versions(datasets.ListVersionsRequest(
            flake.source_id, ProviderSelection(provider.provider_id, provider.scope_id)), context=context))
        assert listed.value.references == (written.value.reference,)
    assert references[0].identity == references[1].identity == encoded.value.identity
    assert references[0].provider_id != references[1].provider_id

    cold_files = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="shared")
    cold_ref = reference_from(reference_value(references[1]))
    cold_read = _assert(datasets.read_snapshot(datasets.ReadSnapshotRequest(cold_ref), store=cold_files))
    assert _assert(read_flake_snapshot(ReadFlakeSnapshotRequest(cold_read.value))).value == flake
    assert cold_read.value.manifest == encoded.value.manifest


def test_partial_table_selection_cannot_pretend_to_be_a_complete_flake(tmp_path):
    flake = _flake("nwf")
    encoded = _assert(build_flake_snapshot(FlakeSnapshotRequest(flake, flake.source_id, "edition-1")))
    backend = MemoryDatasetStore(provider_id="memory", scope_id="application")
    written = _assert(datasets.write_snapshot(datasets.WriteSnapshotRequest(encoded.value), store=backend))
    partial = _assert(datasets.read_snapshot(datasets.ReadSnapshotRequest(written.value.reference, ("metadata",)), store=backend))
    assert not partial.value.complete
    assert partial.value.manifest == encoded.value.manifest
    decoded = read_flake_snapshot(ReadFlakeSnapshotRequest(partial.value))
    assert decoded.outcome == "failed"
    assert decoded.diagnostics[0].code == "minfin.flake.snapshot_invalid"


def test_database_role_change_is_not_a_storage_only_change():
    flake = _flake("budget")
    encoded = _assert(build_flake_snapshot(FlakeSnapshotRequest(flake, flake.source_id, "edition-1"))).value
    different = DatasetSnapshot.build(encoded.manifest.dataset_id, encoded.manifest.version_id,
        DataContract("minfin.flake.snapshot", 1, DataRole.INTEGRATED), encoded.tables,
        coverage=encoded.manifest.coverage, inputs=encoded.manifest.inputs)
    decoded = read_flake_snapshot(ReadFlakeSnapshotRequest(different))
    assert decoded.outcome == "failed"
    assert decoded.diagnostics[0].code == "minfin.flake.snapshot_invalid"


def test_snapshot_output_budget_includes_values_as_well_as_manifest():
    flake = _flake("budget")
    request = FlakeSnapshotRequest(flake, flake.source_id, "edition-1")
    encoded = _assert(build_flake_snapshot(request)).value
    manifest_only = encoded.identity.size
    assert sum(table.identity.size for _, table in encoded.tables) > 0
    refused = build_flake_snapshot(request, context=ExecutionContext(
        budget=ExecutionBudget(output_bytes=manifest_only)))
    assert refused.outcome == "failed" and refused.value is None
    assert refused.diagnostics[0].code == "budget.output_bytes"
