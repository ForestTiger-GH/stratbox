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

from .contracts import CollectedFile, StoredCollectedFile


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
