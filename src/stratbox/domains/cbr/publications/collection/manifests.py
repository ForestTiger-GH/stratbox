"""Portable archive composition for the fixed-file collector wrappers."""
from dataclasses import replace
from pathlib import PurePosixPath
from unicodedata import normalize

from stratbox.core.formats.archives.members import safe_member_name
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.material_collections import (
    CollectionDisposition, CollectionManifest, CollectionMember,
)

from stratbox.domains.cbr.publications.collection.contracts import CollectedFile, StoredCollectedFile


def collection_manifest(collection):
    """Carry the full selected-work disposition through either collection route."""
    base = archive_manifest(collection.completed) if collection.completed else None
    completed = {item.source_id: index for index, item in enumerate(collection.completed)}
    failed = {item.source_id: item.code for item in collection.failed}
    dispositions = []
    for key in collection.selected:
        if key in completed:
            status, diagnostic = "completed", None
        elif collection.unresolved is not None and collection.unresolved.source_id == key:
            status, diagnostic = "unknown", collection.stop_reason
        elif key in failed:
            status, diagnostic = "failed", failed[key]
        elif collection.interrupted is not None and collection.interrupted.source_id == key:
            status, diagnostic = "failed", collection.interrupted.code
        else:
            status, diagnostic = "not_attempted", collection.stop_reason
        dispositions.append(CollectionDisposition(key, status, diagnostic))
    members = tuple(replace(base.members[index], key=key) for key, index in completed.items()) if base else ()
    manifest = CollectionManifest("cbr.selected_originals", "content", members, tuple(dispositions),
        SnapshotCoverage("unknown", "The complete selected-work disposition; publisher history is unspecified."),
        base.inputs if base else ())
    return replace(manifest, version_id=manifest.identity.sha256)


def archive_manifest(files):
    """Identify supplied members without inventing an official release period.

    Fixed URLs identify rolling publications. These wrappers retain the source
    selector and exact bytes; the explicit publication collector additionally
    accepts the caller's issue context and emits source-asset identities.
    """
    if not files:
        raise ValueError("archive.selection_invalid")
    names, members, inputs = {"manifest.json"}, [], []
    for index, item in enumerate(files, 1):
        if not safe_member_name(item.file_name) or "/" in item.file_name or "\\" in item.file_name:
            raise ValueError("request.archive_filename_invalid")
        file = PurePosixPath(item.file_name)
        name, suffix = file.name, 2
        while normalize("NFC", name).casefold() in names:
            name = f"{file.stem}_{suffix}{file.suffix}"
            suffix += 1
        names.add(normalize("NFC", name).casefold())
        if isinstance(item, CollectedFile):
            original = item.source.payload
            availability = "inline"
        elif isinstance(item, StoredCollectedFile) and item.source.material is not None:
            original = item.source.material
            availability = "reference_only"
        else:
            raise ValueError("input.material_unavailable")
        key = f"file.{index:06d}"
        members.append(CollectionMember(key, name, DataContract("source.original", 1, DataRole.ORIGINALS),
            original.identity, original.media_type))
        inputs.append(UsedInputReceipt("archive_member", original.identity, original.media_type,
                                      availability, item.source_id))
    manifest = CollectionManifest("cbr.file_collector.originals", "content", tuple(members),
        tuple(CollectionDisposition(member.key, "completed") for member in members),
        SnapshotCoverage("unknown", "Exactly the supplied files; source history and earlier collection failures are unspecified."),
        tuple(inputs))
    return replace(manifest, version_id=manifest.identity.sha256)
