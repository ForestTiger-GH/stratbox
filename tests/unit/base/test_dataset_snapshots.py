from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from contextlib import contextmanager
import json
import struct

import pytest

from stratbox.core.execution.contracts import ExecutionContext
from stratbox.core.limits import BudgetMeter, ExecutionBudget
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.datasets import DatasetProviders, FileDatasetStore, MemoryDatasetStore
from stratbox.core.storage.datasets.codec import decode_table, encode_table
from stratbox.core.storage.datasets.operations import (ListVersionsRequest, ReadSnapshotRequest, WriteSnapshotRequest,
                                                     list_versions, read_snapshot, write_snapshot)
from stratbox.core.storage.datasets.ports import DatasetReadControls, DatasetStorageError
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import (ColumnSchema, ComponentLink, DatasetAssembly, DatasetManifest, DatasetSnapshot,
    ScalarType, SnapshotCoverage, TableComponent, TableSchema, TypedTable)
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


def table(value=Decimal("10.50")):
    return TypedTable(TableSchema(DataContract("example.amounts", 1, DataRole.EXTRACTS), (
        ColumnSchema("key", ScalarType.TEXT), ColumnSchema("value", ScalarType.DECIMAL, True, "USD")), ("key",)),
        (("a", value), ("b", None)))


def snapshot(version="2026-11", value=Decimal("10.50")):
    return DatasetSnapshot.build("example.series", version, DataContract("example.series", 1, DataRole.EXTRACTS),
        (("values", table(value)),), coverage=SnapshotCoverage("partial", "One observed source issue"),
        inputs=(UsedInputReceipt.for_payload(SourcePayload(b"original", source_id="example.series"), "original"),))


def file_store(tmp_path, **kwargs):
    return FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test", **kwargs)


def test_exact_scalar_roundtrip_preserves_schema_nulls_and_float_bits():
    values = (True, -(2**63), 2**100, -0.0, Decimal("1.2300"), "Text", b"\x00\xff", date(2026, 11, 23),
              datetime(2026, 11, 23, 11, 22, 33, 123456, timezone(timedelta(hours=3))),
              datetime(2026, 11, 23, 11, 22, 33, 123456), timedelta(days=-4, microseconds=7))
    kinds = tuple(ScalarType)
    original = TypedTable(TableSchema(DataContract("example.all_types", role=DataRole.READABLE),
        tuple(ColumnSchema(kind.value, kind, True) for kind in kinds)), (values, (None,) * len(kinds)))
    physical = encode_table(original)
    restored = decode_table(physical, expected_identity=original.identity)
    assert restored.identity == original.identity
    assert restored.schema == original.schema
    assert restored.rows == original.rows
    assert ByteIdentity.of(physical) != original.identity
    assert struct.pack(">d", restored.rows[0][3]) == struct.pack(">d", -0.0)
    assert restored.rows[0][4].as_tuple() == Decimal("1.2300").as_tuple()


def test_float_special_values_preserve_ieee_bits():
    nan = struct.unpack(">d", bytes.fromhex("7ff8000000000007"))[0]
    original = TypedTable(TableSchema(DataContract("example.float"), (ColumnSchema("x", ScalarType.FLOAT64),)),
                          ((nan,), (float("inf"),), (float("-inf"),)))
    restored = decode_table(encode_table(original))
    assert [struct.pack(">d", row[0]) for row in restored.rows] == [struct.pack(">d", row[0]) for row in original.rows]
    assert restored.identity == original.identity


@pytest.mark.parametrize("kind,value", [(ScalarType.BOOLEAN, 1), (ScalarType.INT64, True), (ScalarType.INT64, 2**63),
    (ScalarType.INTEGER, 1.0), (ScalarType.FLOAT64, 1), (ScalarType.DECIMAL, "1.0"), (ScalarType.TEXT, b"x"),
    (ScalarType.BINARY, bytearray(b"x")), (ScalarType.DATE, datetime(2026, 1, 1)),
    (ScalarType.TIMESTAMP, datetime(2026, 1, 1)), (ScalarType.LOCAL_DATETIME, datetime(2026, 1, 1, tzinfo=timezone.utc))])
def test_types_are_explicit_and_never_coerced(kind, value):
    with pytest.raises((ValueError, TypeError)):
        TypedTable(TableSchema(DataContract("example.strict"), (ColumnSchema("x", kind),)), ((value,),))


def test_duplicate_keys_row_width_nulls_and_corrupt_codec_are_rejected():
    schema = TableSchema(DataContract("example.keyed"), (ColumnSchema("id", ScalarType.TEXT),), ("id",))
    for rows in ((("x",), ("x",)), (("x", "extra"),), ((None,),)):
        with pytest.raises((ValueError, TypeError)):
            TypedTable(schema, rows)
    encoded = json.loads(encode_table(table()))
    encoded["rows"][0][1] = "99.9"
    with pytest.raises(ValueError, match="component_mismatch"):
        decode_table(json.dumps(encoded).encode())
    with pytest.raises(ValueError, match="duplicate_json_key"):
        decode_table(b'{"encoding":"x","encoding":"y"}')
    with pytest.raises(ValueError, match="cell_limit"):
        decode_table(encode_table(table()), max_cells=1)


@pytest.mark.parametrize("role", list(DataRole) + [None])
def test_all_data_roles_can_use_same_backends(tmp_path, role):
    original = snapshot()
    original = DatasetSnapshot(replace(original.manifest, contract=DataContract("example.series", 1, role)), original.tables)
    memory = MemoryDatasetStore(provider_id="memory", scope_id="test")
    files = file_store(tmp_path)
    left = memory.write_snapshot(original)
    right = files.write_snapshot(original)
    assert left.status == right.status == "stored"
    assert left.reference.identity == right.reference.identity == original.identity
    assert memory.read_snapshot(left.reference) == files.read_snapshot(right.reference) == original
    assert files.write_snapshot(original).status == "already_present"
    assert files.datasets() == memory.datasets() == ("example.series",)
    assert files.versions("example.series") == (right.reference,)


@pytest.mark.parametrize("adapter", ["memory", "files"])
def test_versions_are_immutable_and_old_snapshots_remain_readable(tmp_path, adapter):
    store = MemoryDatasetStore(provider_id="memory", scope_id="test") if adapter == "memory" else file_store(tmp_path)
    first = store.write_snapshot(snapshot())
    conflict = store.write_snapshot(snapshot(value=Decimal("20.00")))
    assert conflict.status == "failed" and conflict.reference is None
    later = store.write_snapshot(snapshot(version="2026-12", value=Decimal("30.00")))
    assert store.read_snapshot(first.reference).table("values").rows[0][1] == Decimal("10.50")
    assert store.read_snapshot(later.reference).table("values").rows[0][1] == Decimal("30.00")
    with pytest.raises(DatasetStorageError, match="scope_mismatch"):
        store.read_snapshot(replace(first.reference, scope_id="other"))
    with pytest.raises(DatasetStorageError, match="snapshot_mismatch"):
        store.read_snapshot(replace(first.reference, identity=ByteIdentity.of(b"wrong")))


def test_component_selection_preserves_manifest_and_has_no_implicit_concat(tmp_path):
    original = DatasetSnapshot.build("example.multi", "v1", DataContract("example.multi", role=DataRole.INTEGRATED),
        (("first", table()), ("second", table(Decimal("20")))), coverage=SnapshotCoverage("unknown"))
    store = file_store(tmp_path)
    reference = store.write_snapshot(original).reference
    selected = store.read_snapshot(reference, ("second",))
    assert selected.manifest == original.manifest
    assert selected.tables == (("second", table(Decimal("20"))),)
    assert not selected.complete
    assert store.read_snapshot(reference, ()).tables == ()
    with pytest.raises(DatasetStorageError, match="selection_invalid"):
        store.read_snapshot(reference, ("missing",))
    with pytest.raises(DatasetStorageError, match="incomplete_snapshot"):
        store.write_snapshot(selected)
    with pytest.raises(DatasetStorageError, match="cell_limit"):
        store.read_snapshot(reference, controls=DatasetReadControls(max_cells=1))


def test_file_tampering_and_missing_components_fail_before_return(tmp_path):
    store = file_store(tmp_path)
    reference = store.write_snapshot(snapshot()).reference
    physical = next((tmp_path / "datasets" / "tables").rglob("*.json"))
    physical.write_bytes(b"corrupt")
    with pytest.raises(DatasetStorageError, match="physical_identity_mismatch"):
        store.read_snapshot(reference)
    physical.unlink()
    with pytest.raises(DatasetStorageError, match="component_missing"):
        store.read_snapshot(reference)


def test_distributed_assembly_pins_each_parent_and_schema(tmp_path):
    left = MemoryDatasetStore(provider_id="memory", scope_id="left")
    right = file_store(tmp_path)
    refs = (left.write_snapshot(snapshot()).reference, right.write_snapshot(snapshot("2026-12", Decimal("20"))).reference)
    components = (TableComponent.for_table("november", table()), TableComponent.for_table("december", table(Decimal("20"))))
    manifest = DatasetManifest("example.annual", "v1", DataContract("example.series", role=DataRole.EXTRACTS), components,
        SnapshotCoverage("partial", "Two issue snapshots"), parents=tuple(ref.identity for ref in refs))
    assembly = DatasetAssembly(manifest, tuple(ComponentLink(name, ref, "values") for name, ref in zip(("november", "december"), refs)))
    destination = MemoryDatasetStore(provider_id="memory", scope_id="assembly", resolver=DatasetProviders((left, right)))
    reference = destination.write_snapshot(assembly).reference
    restored = destination.read_snapshot(reference)
    assert restored.complete and restored.identity == manifest.identity
    assert tuple(name for name, _ in restored.tables) == ("november", "december")
    assert restored.table("december").rows[0][1] == Decimal("20")
    selected = destination.read_snapshot(reference, ("december",))
    assert len(selected.tables) == 1 and not selected.complete
    destination.resolver = DatasetProviders((left,))
    with pytest.raises(DatasetStorageError, match="provider_unavailable"):
        destination.read_snapshot(reference)
    # A missing unrelated provider does not block an explicitly selected table.
    assert destination.read_snapshot(reference, ("november",)).table("november") == table()


def test_file_assembly_replays_without_copying_components(tmp_path):
    source = MemoryDatasetStore(provider_id="memory", scope_id="source")
    reference = source.write_snapshot(snapshot()).reference
    manifest = DatasetManifest("example.composed", "v1", snapshot().manifest.contract,
        (TableComponent.for_table("linked", table()),), SnapshotCoverage("unknown"), parents=(reference.identity,))
    assembly = DatasetAssembly(manifest, (ComponentLink("linked", reference, "values"),))
    destination = file_store(tmp_path, resolver=DatasetProviders((source,)))
    stored = destination.write_snapshot(assembly)
    assert stored.status == "stored"
    assert destination.read_snapshot(stored.reference).table("linked") == table()
    assert not (tmp_path / "datasets" / "tables").exists()


def test_operation_result_chaining_uses_selected_dataset_adapter(tmp_path):
    store = file_store(tmp_path)
    bindings = tuple(ProviderBinding("files", CapabilityRequirement(role), "ready", store, "test")
        for role in ("dataset_reader", "dataset_writer", "dataset_catalog"))
    context = ExecutionContext(bindings=bindings)
    written = write_snapshot(WriteSnapshotRequest(snapshot(), ProviderSelection("files", "test")), context=context)
    assert written.outcome == "succeeded", written.diagnostics
    assert written.value.reference is not None
    assert any(e.kind == "dataset.write" and e.state == "confirmed" for e in written.effects)
    read = read_snapshot(ReadSnapshotRequest(written.value.reference), context=context)
    assert read.outcome == "succeeded", read.diagnostics
    assert read.value == snapshot()
    assert read.used_inputs and read.computation
    listed = list_versions(ListVersionsRequest("example.series", ProviderSelection("files", "test")), context=context)
    assert listed.outcome == "succeeded"
    assert listed.value.references == (written.value.reference,)


def test_managed_dataset_bindings_require_scope_and_commit_guarantees():
    store = MemoryDatasetStore(provider_id="memory", scope_id="test")
    context = ExecutionContext(profile="managed", bindings=(
        ProviderBinding("memory", CapabilityRequirement("dataset_writer"), "ready", store, "test"),))
    denied = write_snapshot(WriteSnapshotRequest(snapshot()), context=context)
    assert denied.outcome == "failed"
    assert any(d.code == "provider.guarantee_missing" for d in denied.diagnostics)
    allowed = replace(context, bindings=(ProviderBinding("memory", CapabilityRequirement("dataset_writer", guarantees=frozenset({"scope_bound", "verified_commit"})), "ready", store, "test"),))
    assert write_snapshot(WriteSnapshotRequest(snapshot()), context=allowed).outcome == "succeeded"


class LostManifestAcknowledgement:
    def __init__(self, store):
        self.store = store

    def __getattr__(self, name):
        return getattr(self.store, name)

    @contextmanager
    def stage_write(self, destination):
        with self.store.stage_write(destination) as stage:
            if "/versions/" not in destination:
                yield stage
                return
            class LostStage:
                stream = stage.stream
                def commit(self, mode, expected_revision):
                    stage.commit(mode, expected_revision)
                    raise OSError("Acknowledgement lost")
            yield LostStage()


def test_lost_manifest_acknowledgement_has_no_confirmed_reference(tmp_path):
    underlying = LocalFileStore(str(tmp_path))
    store = FileDatasetStore(LostManifestAcknowledgement(underlying), "datasets", provider_id="files", scope_id="test")
    result = write_snapshot(WriteSnapshotRequest(snapshot()), store=store)
    assert result.outcome == "unknown", result.diagnostics
    assert result.value.reference is None
    assert any(e.kind == "dataset.write" and e.state == "unknown" for e in result.effects)
    # A subsequent explicit immutable retry verifies the completed version.
    reconciled = write_snapshot(WriteSnapshotRequest(snapshot()), store=store)
    assert reconciled.outcome == "succeeded"
    assert reconciled.value.status == "already_present"


def test_logical_identity_changes_with_schema_coverage_lineage_or_values():
    original = snapshot()
    changed = [snapshot(value=Decimal("10.500")), snapshot("next"),
        DatasetSnapshot(replace(original.manifest, coverage=SnapshotCoverage("complete")), original.tables),
        DatasetSnapshot(replace(original.manifest, inputs=()), original.tables)]
    assert all(value.identity != original.identity for value in changed)


def test_input_availability_does_not_change_logical_identity():
    original = snapshot()
    retained = replace(original.manifest, inputs=(replace(original.manifest.inputs[0], availability="reference_only"),))
    assert retained.identity == original.identity
    assert retained.inputs != original.manifest.inputs


def test_write_object_limit_fails_without_visible_version(tmp_path):
    store = file_store(tmp_path, max_object_bytes=128)
    result = write_snapshot(WriteSnapshotRequest(snapshot()), store=store)
    assert result.outcome == "failed", result.diagnostics
    assert result.value is None
    assert store.versions("example.series") == ()
    assert all(effect.state != "unknown" for effect in result.effects)


def test_output_budget_failure_before_commit_is_known_failure(tmp_path):
    result = write_snapshot(WriteSnapshotRequest(snapshot()), store=file_store(tmp_path),
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=1)))
    assert result.outcome == "failed", result.diagnostics
    assert not any(effect.state == "unknown" for effect in result.effects)


def test_input_byte_budget_is_applied_to_memory_and_file_reads(tmp_path):
    for store in (MemoryDatasetStore(provider_id="memory", scope_id="test"), file_store(tmp_path)):
        reference = store.write_snapshot(snapshot()).reference
        result = read_snapshot(ReadSnapshotRequest(reference), store=store,
            context=ExecutionContext(budget=ExecutionBudget(input_bytes=1)))
        assert result.outcome == "failed"
        assert any(d.code.startswith("budget.") for d in result.diagnostics)
