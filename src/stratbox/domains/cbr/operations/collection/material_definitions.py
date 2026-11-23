"""Mixed-original collection contracts, independent of acquisition handlers."""
from dataclasses import dataclass, field
from stratbox.core.operations.materials.archive_definitions import ArchiveMember

from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.core.runtime.capabilities import ProviderSelection
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import MaterialReference, SourcePayload
from stratbox.shared.material_collections import CollectionManifest


@dataclass(frozen=True, slots=True)
class CollectMaterial:
    key: str
    series_id: str
    issue_id: str
    format: str
    payload: SourcePayload | None = None
    material: MaterialReference | None = None
    url: str | None = None
    selection: ProviderSelection | None = None
    asset_id: str = "main"
    name: str | None = None


@dataclass(frozen=True, slots=True)
class CollectMaterialsRequest:
    items: tuple[CollectMaterial, ...]
    continue_on_error: bool = True
    max_batch_bytes: int = 256 * 1024**2


@dataclass(frozen=True, slots=True)
class MaterialCollection:
    originals: tuple[tuple[str, IdentifiedOriginal], ...]
    manifest: CollectionManifest
    archive_members: tuple[ArchiveMember, ...] = field(init=False)

    def __post_init__(self):
        originals = dict(self.originals)
        if (len(originals) != len(self.originals) or set(originals) != {item.key for item in self.manifest.members}
                or any(originals[item.key].payload.identity != item.identity for item in self.manifest.members)):
            raise ValueError("cbr.collection.manifest_mismatch")
        object.__setattr__(self, "archive_members", tuple(ArchiveMember(item.name, originals[item.key].payload)
                                                        for item in self.manifest.members))


COLLECT_MATERIALS = OperationDefinition("cbr.file_collector.collect_materials", 1,
    "cbr-mixed-originals-v1", CollectMaterialsRequest, MaterialCollection,
    optional_capabilities=frozenset({"http", "filestore"}), partial_allowed=True,
    limits=ExecutionBudget(input_bytes=256 * 1024**2, output_bytes=256 * 1024**2,
                           temporary_bytes=256 * 1024**2, cells=5_000_000),
    processing=OperationSemantics((ProcessingStage.ACQUIRE, ProcessingStage.INSPECT),
        outputs=(OutputPort("collection", DataContract("cbr.material_collection"),
                            outcomes=frozenset({"succeeded", "partial"})),
                 OutputPort("manifest", DataContract("material.collection"), "manifest",
                            outcomes=frozenset({"succeeded", "partial"})),
                 OutputPort("archive_members", DataContract("material.archive_members"), "archive_members",
                            outcomes=frozenset({"succeeded", "partial"}))),
        parameters=("items", "continue_on_error", "max_batch_bytes"), composition=True,
        summary="Acquire independently supplied original routes and return exact materials with per-item dispositions."))
