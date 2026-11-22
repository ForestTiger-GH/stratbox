"""Physical bindings are invocation arguments; requests describe exact values."""
from dataclasses import dataclass, field

from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.core.operations.source.original_definitions import OriginalDestination, StoredOriginal
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.evidence import MaterialReference, SourcePayload, StoredBytesReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.materials import ArtifactReference, MaterialArtifact

MAX_BYTES = 512 * 1024 * 1024
LIMITS = ExecutionBudget(input_bytes=MAX_BYTES, output_bytes=MAX_BYTES, temporary_bytes=MAX_BYTES)


@dataclass(frozen=True, slots=True)
class ReadLocationRequest:
    locator: str = field(repr=False)
    media_type: str = "application/octet-stream"
    source_id: str | None = None
    expected_identity: ByteIdentity | None = None
    expected_revision: str | None = field(default=None, repr=False)
    limit: int = 64 * 1024 * 1024
    charset: str | None = None


@dataclass(frozen=True, slots=True)
class LocatedMaterial:
    payload: SourcePayload
    material: MaterialReference


@dataclass(frozen=True, slots=True)
class TransferMaterialRequest:
    material: MaterialReference
    destination: OriginalDestination


@dataclass(frozen=True, slots=True)
class ArtifactDestination:
    """Two immutable objects; a confirmed descriptor publishes the whole value."""
    locator: str = field(repr=False)
    descriptor_locator: str | None = field(default=None, repr=False)

    @property
    def descriptor(self):
        return self.descriptor_locator or self.locator + ".stratbox.json"


@dataclass(frozen=True, slots=True)
class SaveArtifactRequest:
    artifact: MaterialArtifact
    destination: ArtifactDestination


@dataclass(frozen=True, slots=True)
class ReadArtifactRequest:
    artifact: ArtifactReference
    limit: int = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class TransferArtifactRequest:
    artifact: ArtifactReference
    destination: ArtifactDestination


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    artifact: ArtifactReference | None
    storage: tuple[StoredBytesReceipt, ...]


READ_LOCATION = OperationDefinition(
    "material.read_location", 2, "bounded-neutral-file-read-2", ReadLocationRequest, LocatedMaterial,
    frozenset({"filestore"}), limits=LIMITS,
    processing=OperationSemantics(stages=(ProcessingStage.ACQUIRE,),
        outputs=(OutputPort("source", DataContract("material.payload"), path="payload"),
                 OutputPort("material", DataContract("material.reference"), path="material",
                            qualifications=frozenset({"storage.confirmed"}))),
        parameters=("locator", "media_type", "source_id", "expected_identity", "expected_revision", "limit", "charset"),
        summary="Read an explicitly supplied store location and establish exact byte identity."))

TRANSFER = OperationDefinition(
    "material.transfer", 2, "verified-neutral-stream-copy-2", TransferMaterialRequest, StoredOriginal,
    frozenset({"filestore", "output_filestore"}), frozenset({"storage.write"}), limits=LIMITS,
    processing=OperationSemantics(stages=(ProcessingStage.PRESERVE,),
        inputs=(InputPort("material", DataContract("material.reference"), path="material",
                          alternatives=(DataContract("source.material_reference", 1, DataRole.ORIGINALS),)),),
        outputs=(OutputPort("material", DataContract("material.reference"), path="material",
                            qualifications=frozenset({"storage.confirmed"})),), parameters=("destination",),
        summary="Stream an exact material between independently selected stores without deleting its source."))

SAVE_ARTIFACT = OperationDefinition(
    "material.save_artifact", 1, "artifact-publish-1", SaveArtifactRequest, StoredArtifact,
    frozenset({"output_filestore"}), frozenset({"storage.write"}), limits=LIMITS,
    processing=OperationSemantics(stages=(ProcessingStage.PRESERVE,),
        inputs=(InputPort("artifact", DataContract("material.artifact"), path="artifact"),),
        outputs=(OutputPort("artifact", DataContract("material.artifact_reference"), path="artifact",
                            qualifications=frozenset({"storage.confirmed"})),), parameters=("destination",),
        summary="Retain exact representation bytes and a complete immutable semantic descriptor."))

READ_ARTIFACT = OperationDefinition(
    "material.read_artifact", 1, "artifact-replay-1", ReadArtifactRequest, MaterialArtifact,
    frozenset({"filestore"}), optional_capabilities=frozenset({"descriptor_filestore"}), limits=LIMITS,
    processing=OperationSemantics(stages=(ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("artifact", DataContract("material.artifact_reference"), path="artifact"),),
        outputs=(OutputPort("artifact", DataContract("material.artifact")),), parameters=("limit",),
        summary="Restore and verify a retained artifact's contract, representation and full lineage."))

TRANSFER_ARTIFACT = OperationDefinition(
    "material.transfer_artifact", 1, "artifact-copy-1", TransferArtifactRequest, StoredArtifact,
    frozenset({"filestore", "output_filestore"}), frozenset({"storage.write"}),
    optional_capabilities=frozenset({"descriptor_filestore"}), limits=LIMITS,
    processing=OperationSemantics(stages=(ProcessingStage.PRESERVE,),
        inputs=(InputPort("artifact", DataContract("material.artifact_reference"), path="artifact"),),
        outputs=(OutputPort("artifact", DataContract("material.artifact_reference"), path="artifact",
                            qualifications=frozenset({"storage.confirmed"})),), parameters=("destination",),
        summary="Copy a complete retained value to a different store while preserving its descriptor identity."))
