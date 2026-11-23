"""Typed declarations for universal archive packaging."""

from stratbox.operations.declarations import definition as _registry_definition
from dataclasses import dataclass
from stratbox.core.formats.archives.store import ArchiveWriteLimits, PathArchiveReceipt
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.runtime.capabilities import ProviderSelection
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import MaterialReference, SourcePayload, UsedInputReceipt
from stratbox.shared.material_collections import CollectionManifest
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
    manifest: CollectionManifest | None = None
    manifest_name: str = "manifest.json"
    limits: ArchiveWriteLimits = ArchiveWriteLimits()


@dataclass(frozen=True, slots=True)
class StoredArchive:
    archive: PathArchiveReceipt
    material: MaterialReference | None
    members: tuple[tuple[str, UsedInputReceipt], ...]
    manifest: CollectionManifest


ARCHIVE = _registry_definition('material.archive')
