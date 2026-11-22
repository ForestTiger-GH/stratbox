from contextlib import contextmanager
from dataclasses import replace

import pytest

from stratbox.core.operations.materials.definitions import ArtifactDestination, ReadArtifactRequest, SaveArtifactRequest, TransferArtifactRequest
from stratbox.core.operations.materials.operations import read_artifact, save_artifact, transfer_artifact
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.materials import ArtifactReference, MaterialArtifact
from stratbox.shared.source_publications import SourceAssetIdentity


def good(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


@pytest.mark.parametrize("role", tuple(DataRole))
def test_every_role_preserves_representation_semantics_and_lineage_across_stores(tmp_path, role):
    a, b = LocalFileStore(str(tmp_path / "a")), LocalFileStore(str(tmp_path / "b"))
    original = SourcePayload(b"%PDF-1.7\nsource", "application/pdf", "publisher.report")
    artifact = MaterialArtifact(DataContract("sample.value", 3, role),
        Representation("sample.utf8", 2, "text/plain", b"retained content", "utf-8"),
        (UsedInputReceipt.for_payload(original, "original"),), "publisher.report",
        SourceAssetIdentity("publisher.report", "2026-10", "main_pdf"))
    retained = good(save_artifact(SaveArtifactRequest(artifact, ArtifactDestination("value.txt")), store=a))
    assert a.read_bytes("value.txt") == artifact.representation.data
    assert a.read_bytes("value.txt.stratbox.json") == artifact.descriptor
    # This portable reference is all a new consumer needs, with its providers.
    reference = ArtifactReference.from_bytes(retained.artifact.to_bytes())
    copied = good(transfer_artifact(TransferArtifactRequest(reference, ArtifactDestination("moved.txt")),
                                   source_store=a, output_store=b))
    assert copied.artifact.identity == reference.identity
    restored = good(read_artifact(ReadArtifactRequest(copied.artifact), store=b))
    assert restored == artifact
    assert restored.source_asset.issue_id == "2026-10"
    assert all(x.status in {"stored", "already_present"} for x in copied.storage)


def test_bad_data_descriptor_or_claimed_role_cannot_restore(tmp_path):
    store = LocalFileStore(str(tmp_path))
    artifact = MaterialArtifact(DataContract("sample", 1, DataRole.EXTRACTS), Representation("sample", 1, "text/plain", b"data"))
    ref = good(save_artifact(SaveArtifactRequest(artifact, ArtifactDestination("data")), store=store)).artifact
    forged = replace(ref, contract=DataContract("sample", 1, DataRole.INTEGRATED))
    assert read_artifact(ReadArtifactRequest(forged), store=store).outcome == "failed"
    store.write_bytes("data", b"evil")
    assert read_artifact(ReadArtifactRequest(ref), store=store).outcome == "failed"


def test_descriptor_lost_ack_is_unknown_and_does_not_publish_a_reference(tmp_path):
    class LostAckStore(LocalFileStore):
        @contextmanager
        def stage_write(self, destination):
            with super().stage_write(destination) as stage:
                class Stage:
                    @property
                    def stream(self):
                        return stage.stream
                    def commit(self, mode, revision):
                        result = stage.commit(mode, revision)
                        if destination.endswith(".stratbox.json"):
                            raise ConnectionError("synthetic lost acknowledgement")
                        return result
                yield Stage()
    store = LostAckStore(str(tmp_path))
    artifact = MaterialArtifact(DataContract("sample"), Representation("sample", 1, "text/plain", b"data"))
    result = save_artifact(SaveArtifactRequest(artifact, ArtifactDestination("data")), store=store)
    assert result.outcome == "unknown"
    assert result.value.artifact is None
    assert [x.state for x in result.effects] == ["confirmed", "unknown"]
    assert store.exists("data") and store.exists("data.stratbox.json")


def test_immutable_retry_and_descriptor_conflict_remain_explicit(tmp_path):
    store = LocalFileStore(str(tmp_path))
    artifact = MaterialArtifact(DataContract("sample"), Representation("sample", 1, "text/plain", b"data"))
    request = SaveArtifactRequest(artifact, ArtifactDestination("data"))
    first = good(save_artifact(request, store=store))
    retry = good(save_artifact(request, store=store))
    assert retry.artifact == first.artifact
    assert all(x.status == "already_present" for x in retry.storage)
    changed = replace(artifact, contract=DataContract("changed"))
    result = save_artifact(SaveArtifactRequest(changed, ArtifactDestination("data")), store=store)
    assert result.outcome == "failed" and result.value.artifact is None
    assert store.read_bytes("data.stratbox.json") == artifact.descriptor
