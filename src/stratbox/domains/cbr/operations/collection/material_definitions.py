"""Mixed-original collection contracts, independent of acquisition handlers."""

from stratbox.operations.declarations import definition as _registry_definition
from dataclasses import dataclass, field
from stratbox.core.operations.materials.archive_definitions import ArchiveMember

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


COLLECT_MATERIALS = _registry_definition('cbr.file_collector.collect_materials')
