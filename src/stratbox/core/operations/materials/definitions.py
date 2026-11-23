"""Physical bindings are invocation arguments; requests describe exact values."""

from stratbox.core.registry.operations import definition as _registry_definition
from dataclasses import dataclass, field

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


READ_LOCATION = _registry_definition('material.read_location')

TRANSFER = _registry_definition('material.transfer')

SAVE_ARTIFACT = _registry_definition('material.save_artifact')

READ_ARTIFACT = _registry_definition('material.read_artifact')

TRANSFER_ARTIFACT = _registry_definition('material.transfer_artifact')
