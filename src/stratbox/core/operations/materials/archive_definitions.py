"""Typed declarations for universal archive packaging."""
from dataclasses import dataclass
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.formats.archives.store import PathArchiveReceipt
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.runtime.capabilities import ProviderSelection
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import MaterialReference, SourcePayload, UsedInputReceipt
from .definitions import LIMITS


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    name: str
    source: SourcePayload | MaterialReference
    selection: ProviderSelection | None = None


@dataclass(frozen=True, slots=True)
class ArchiveRequest:
    members: tuple[ArchiveMember, ...]
    destination: OriginalDestination
    compression: str = "stored"


@dataclass(frozen=True, slots=True)
class StoredArchive:
    archive: PathArchiveReceipt
    material: MaterialReference | None
    members: tuple[tuple[str, UsedInputReceipt], ...]


ARCHIVE = OperationDefinition(
    "material.archive", 1, "verified-archive-1", ArchiveRequest, StoredArchive,
    frozenset({"output_filestore"}), frozenset({"storage.write"}),
    optional_capabilities=frozenset({"filestore"}), limits=LIMITS,
    processing=OperationSemantics(stages=(ProcessingStage.PRESERVE,),
        outputs=(OutputPort("archive", DataContract("material.archive_reference"), path="material",
                            qualifications=frozenset({"storage.confirmed"})),),
        parameters=("members", "destination", "compression"),
        summary="Package selected exact byte members from independent stores with explicit member lineage."))

