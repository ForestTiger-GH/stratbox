from dataclasses import replace

from stratbox.core.execution import ExecutionContext
from stratbox.core.execution.handoff import project_output
from stratbox.core.operations.materials.definitions import ReadLocationRequest, TransferMaterialRequest
from stratbox.core.operations.materials.operations import read_location, transfer_material
from stratbox.core.operations.source.original_definitions import OriginalDestination, ReadOriginalRequest
from stratbox.core.operations.source.originals import read_original
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.identity import ByteIdentity


def binding(name, role, store):
    return ProviderBinding(name, CapabilityRequirement(role), "ready", store, scope_id=name)


def good(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def test_named_read_and_transfer_use_independent_stores_and_exact_revisions(tmp_path):
    a, b = LocalFileStore(str(tmp_path / "a")), LocalFileStore(str(tmp_path / "b"))
    a.write_bytes("original.pdf", b"%PDF-1.7\nexact bytes\x00\xff")
    b.write_bytes("original.pdf", b"different data at the same relative address")
    context = ExecutionContext(bindings=(binding("source", "filestore", a), binding("other", "filestore", b),
                                         binding("sink", "output_filestore", b)))
    observed = read_location(ReadLocationRequest("original.pdf", "application/pdf", "publisher.report"),
                             selection=ProviderSelection("source"), context=context)
    value = good(observed)
    assert project_output(observed, "material").value == value.material
    assert value.payload.identity == ByteIdentity.of(a.read_bytes("original.pdf"))
    copied = good(transfer_material(TransferMaterialRequest(value.material, OriginalDestination("copy.pdf")),
                 source_selection=ProviderSelection("source"), output_selection=ProviderSelection("sink"), context=context))
    assert copied.material.identity == value.payload.identity
    assert copied.material.store_scope != value.material.store_scope
    assert good(read_original(ReadOriginalRequest(copied.material), store=b)).data == value.payload.data
    assert a.exists("original.pdf")
    wrong = read_original(ReadOriginalRequest(value.material), store=b)
    assert wrong.outcome == "failed" and wrong.diagnostics[0].code == "input.material_store_mismatch"


def test_explicit_missing_location_or_selection_never_falls_back(tmp_path):
    store = LocalFileStore(str(tmp_path))
    context = ExecutionContext(bindings=(binding("disk", "filestore", store),))
    for request, selection in ((ReadLocationRequest("absent.pdf"), ProviderSelection("disk")),
                               (ReadLocationRequest("anything"), ProviderSelection("absent"))):
        result = read_location(request, selection=selection, context=context)
        assert result.outcome == "failed" and result.value is None
        assert not result.effects


def test_changed_source_and_expected_identity_stop_before_copy(tmp_path):
    store = LocalFileStore(str(tmp_path))
    store.write_bytes("input", b"first")
    original = good(read_location(ReadLocationRequest("input"), store=store))
    bad = read_location(ReadLocationRequest("input", expected_identity=ByteIdentity.of(b"wrong")), store=store)
    assert bad.outcome == "failed"
    store.write_bytes("input", b"later")
    result = transfer_material(TransferMaterialRequest(original.material, OriginalDestination("output")),
                               source_store=store, output_store=store)
    assert result.outcome == "failed" and not store.exists("output") and not result.effects
    # Hash verification remains mandatory when no revision facility is available.
    result = read_original(ReadOriginalRequest(replace(original.material, revision=None)), store=store)
    assert result.outcome == "failed" and result.diagnostics[0].code == "input.identity_mismatch"
