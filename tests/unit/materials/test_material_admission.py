"""Adversarial admission of retained metadata, scoped readers and archives."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.core.execution.handoff import HandoffError, project_output
from stratbox.core.limits import ExecutionBudget
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.materials.definitions import (
    ArtifactDestination, ReadArtifactRequest, ReadLocationRequest, SaveArtifactRequest, TransferArtifactRequest,
)
from stratbox.core.operations.materials.operations import read_artifact, read_location, save_artifact, transfer_artifact
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.shared.materials import MaterialArtifact, restore_artifact


def artifact(*, computation=False):
    original = SourcePayload(b"publisher bytes", "application/octet-stream", "sample.series")
    representation = Representation("sample.flake", 1, "application/json", b'{"value":5}', "utf-8")
    receipt = None
    if computation:
        definition = OperationDefinition("sample.serialize", 1, "serialize-1", int, Representation)
        receipt = run(definition, 1, lambda req, inv: representation).computation
    return MaterialArtifact(DataContract("sample.flake.json", role=DataRole.EXTRACTS), representation,
        (UsedInputReceipt.for_payload(original, "original"),), "sample.series", computation=receipt)


def good(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


@pytest.mark.parametrize("field,value", [
    ("media_type", 123),
    ("source_id", ["untyped"]),
    ("member", 5),
])
def test_retained_input_receipts_are_structurally_typed(field, value):
    item = artifact()
    descriptor = json.loads(item.descriptor)
    descriptor["inputs"][0][field] = value
    if field == "member":
        descriptor["inputs"][0]["container"] = descriptor["inputs"][0]["identity"]
    with pytest.raises(ValueError):
        restore_artifact(canonical_manifest_bytes(descriptor), item.representation.data)


@pytest.mark.parametrize("field,value", [("profile_id", 123), ("version", True), ("encoding", 123)])
def test_retained_representation_metadata_has_strict_types(field, value):
    item = artifact()
    descriptor = json.loads(item.descriptor)
    descriptor["representation"][field] = value
    with pytest.raises(ValueError):
        restore_artifact(canonical_manifest_bytes(descriptor), item.representation.data)


@pytest.mark.parametrize("case", ["null_parent", "duplicate_parent", "version_disagrees_with_manifest"])
def test_retained_computation_is_structurally_and_internally_consistent(case):
    item = artifact(computation=True)
    descriptor = json.loads(item.descriptor)
    evidence = descriptor["computation"]
    if case == "null_parent":
        evidence["parents"] = [["source", None]]
    elif case == "duplicate_parent":
        parent = deepcopy(evidence)
        evidence["parents"] = [["source", parent], ["source", parent]]
    else:
        evidence["version"]["method_version"] = "changed-method"
    with pytest.raises(ValueError):
        restore_artifact(canonical_manifest_bytes(descriptor), item.representation.data)


def test_transfer_counts_each_read_byte_once(tmp_path):
    source = LocalFileStore(str(tmp_path / "source"))
    destination = LocalFileStore(str(tmp_path / "destination"))
    item = artifact()
    reference = good(save_artifact(SaveArtifactRequest(item, ArtifactDestination("value")), store=source)).artifact
    exact_input = len(item.representation.data) + len(item.descriptor)
    result = transfer_artifact(TransferArtifactRequest(reference, ArtifactDestination("copy")),
        source_store=source, output_store=destination,
        context=ExecutionContext(budget=ExecutionBudget(input_bytes=exact_input)))
    assert result.outcome == "succeeded", result.diagnostics
    assert dict(result.resources_used)["input_bytes"] == exact_input
    assert good(read_artifact(ReadArtifactRequest(result.value.artifact), store=destination)) == item


def test_separate_descriptor_reader_requires_its_own_managed_scope_guarantee(tmp_path):
    source = LocalFileStore(str(tmp_path / "source"))
    metadata = LocalFileStore(str(tmp_path / "metadata"))
    item = artifact()
    reference = good(save_artifact(SaveArtifactRequest(item, ArtifactDestination("value")), store=source)).artifact
    metadata.write_bytes("descriptor", item.descriptor)
    meta_ref = good(read_location(ReadLocationRequest("descriptor", "application/json", "sample.series"), store=metadata)).material
    reference = replace(reference, descriptor=meta_ref)
    reader = ProviderBinding("reader", CapabilityRequirement("filestore", guarantees=frozenset({"scope_bound"})),
        "ready", source, "source")
    descriptor = ProviderBinding("metadata", CapabilityRequirement("descriptor_filestore"), "ready", metadata, "metadata")
    context = ExecutionContext(profile="managed", bindings=(reader, descriptor))
    options = {"selection": ProviderSelection("reader"), "descriptor_selection": ProviderSelection("metadata")}
    rejected = read_artifact(ReadArtifactRequest(reference), context=context, **options)
    assert rejected.outcome == "failed"
    assert rejected.diagnostics[0].code == "provider.guarantee_missing"
    qualified = replace(descriptor, capability=CapabilityRequirement("descriptor_filestore", guarantees=frozenset({"scope_bound"})))
    result = read_artifact(ReadArtifactRequest(reference), context=replace(context, bindings=(reader, qualified)), **options)
    assert good(result) == item


def test_archive_cannot_replace_an_original_even_when_reference_has_no_scope_hint(tmp_path):
    store = LocalFileStore(str(tmp_path))
    original = b"exact publisher original"
    store.write_bytes("original", original)
    reference = good(read_location(ReadLocationRequest("original"), store=store)).material
    reference = replace(reference, store_scope=None)
    result = archive_materials(ArchiveRequest((ArchiveMember("member.bin", reference),),
        OriginalDestination("original", "replace_expected_revision", reference.revision)),
        source_store=store, output_store=store)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "archive.source_destination_conflict"
    assert not result.effects
    assert store.read_bytes("original") == original


def test_archive_lost_ack_stays_unknown_and_cannot_feed_a_confirmed_output(tmp_path):
    class LostAck(LocalFileStore):
        @contextmanager
        def stage_write(self, destination):
            with super().stage_write(destination) as stage:
                class Uncertain:
                    stream = stage.stream

                    def commit(self, mode, revision):
                        stage.commit(mode, revision)
                        raise ConnectionError("Synthetic lost acknowledgement")
                yield Uncertain()

    writer = LostAck(str(tmp_path))
    result = archive_materials(ArchiveRequest((ArchiveMember("member.pdf", SourcePayload(b"%PDF-1.7\nsource", "application/pdf")),),
        OriginalDestination("archive.zip")), output_store=writer)
    assert result.outcome == "unknown"
    assert result.value.material is None
    assert writer.exists("archive.zip")
    assert len(result.effects) == 1 and result.effects[0].state == "unknown"
    with pytest.raises(HandoffError, match="outcome_not_accepted"):
        project_output(result, "archive")


def test_descriptor_budget_refusal_exposes_confirmed_data_without_publishing_artifact(tmp_path):
    writer = LocalFileStore(str(tmp_path))
    item = artifact()
    result = save_artifact(SaveArtifactRequest(item, ArtifactDestination("value")), store=writer,
        context=ExecutionContext(budget=ExecutionBudget(output_bytes=len(item.representation.data))))
    assert result.outcome == "failed"
    assert result.value is None
    assert len(result.effects) == 1 and result.effects[0].state == "confirmed"
    assert writer.read_bytes("value") == item.representation.data
    assert not writer.exists("value.stratbox.json")
