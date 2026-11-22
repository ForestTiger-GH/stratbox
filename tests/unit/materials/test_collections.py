from dataclasses import replace
from io import BytesIO
from zipfile import ZipFile

import pytest

from stratbox.core.execution.handoff import project_output
from stratbox.core.formats.archives.store import ArchiveWriteLimits
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.materials.collections import read_collection, serialize_collection
from stratbox.core.operations.materials.definitions import ReadLocationRequest
from stratbox.core.operations.materials.operations import read_location
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.material_collections import (
    CollectionDisposition, CollectionManifest, CollectionMember, decode_collection,
)


def test_manifest_preserves_partial_selection_and_all_semantic_roles(tmp_path):
    raw = SourcePayload(b"original")
    product = SourcePayload(b"workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    members = (
        CollectionMember("source", "2026/101/source.dbf", DataContract("cbr.forms.dbf", 1, DataRole.ORIGINALS), raw.identity),
        CollectionMember("view", "views/escrow.xlsx", DataContract("cbr.escrow.workbook", 1, DataRole.PRODUCTS),
                         product.identity, product.media_type),
    )
    manifest = CollectionManifest("example.collection", "v1", members, (
        CollectionDisposition("source", "completed"), CollectionDisposition("missing", "failed", "source.unavailable"),
        CollectionDisposition("view", "completed")), SnapshotCoverage("unknown", "Selected material only."))
    encoded = serialize_collection(manifest)
    assert encoded.outcome == "succeeded", encoded.diagnostics
    replay = read_collection(encoded.value)
    assert replay.outcome == "succeeded" and replay.value == manifest
    assert not replay.value.complete
    out = LocalFileStore(str(tmp_path))
    result = archive_materials(ArchiveRequest((ArchiveMember(members[0].name, raw), ArchiveMember(members[1].name, product)),
                              OriginalDestination("bundle.zip"), manifest=manifest), output_store=out)
    assert result.outcome == "succeeded", result.diagnostics
    with ZipFile(BytesIO(out.read_bytes("bundle.zip"))) as archive:
        assert decode_collection(archive.read("manifest.json")) == manifest
        assert set(archive.namelist()) == {members[0].name, members[1].name, "manifest.json"}
    assert result.value.manifest.identity == manifest.identity


def test_archive_rejects_material_missing_from_manifest_before_writing(tmp_path):
    raw = SourcePayload(b"data")
    member = CollectionMember("a", "data.csv", DataContract("example.flake", 1, DataRole.EXTRACTS), raw.identity)
    manifest = CollectionManifest("example", "v1", (member,), (CollectionDisposition("a", "completed"),),
                                  SnapshotCoverage("unknown"))
    store = LocalFileStore(str(tmp_path))
    result = archive_materials(ArchiveRequest((ArchiveMember("partial.csv", raw),),
                              OriginalDestination("bad.zip"), manifest=manifest), output_store=store)
    assert result.outcome == "failed" and result.diagnostics[0].code == "archive.manifest_mismatch"
    assert not result.effects and not store.exists("bad.zip")


def test_archive_nested_paths_and_caller_bound_support_more_than_500_members(tmp_path):
    store = LocalFileStore(str(tmp_path))
    members = tuple(ArchiveMember(f"2026/101/table-{i}.csv", SourcePayload(str(i).encode())) for i in range(501))
    result = archive_materials(ArchiveRequest(members, OriginalDestination("many.zip"),
                              limits=ArchiveWriteLimits(members=502)), output_store=store)
    assert result.outcome == "succeeded", result.diagnostics
    with ZipFile(BytesIO(store.read_bytes("many.zip"))) as archive:
        assert len(archive.namelist()) == 502
        assert archive.read("2026/101/table-500.csv") == b"500"


@pytest.mark.parametrize("names", [("file", "file/child"), ("a/b", "a/B"), ("dir\\file",), ("dir/../file",)])
def test_archive_rejects_path_aliases_and_file_parent_conflicts(tmp_path, names):
    store = LocalFileStore(str(tmp_path))
    result = archive_materials(ArchiveRequest(tuple(ArchiveMember(name, SourcePayload(b"x")) for name in names),
                              OriginalDestination("invalid.zip")), output_store=store)
    assert result.outcome == "failed" and not store.exists("invalid.zip")


def test_reading_an_unclassified_file_does_not_assert_original_role(tmp_path):
    store = LocalFileStore(str(tmp_path))
    store.write_bytes("product.xlsx", b"some retained representation")
    result = read_location(ReadLocationRequest("product.xlsx"), store=store)
    assert result.outcome == "succeeded"
    assert project_output(result, "source").contract == DataContract("material.payload")
    assert project_output(result, "material").contract == DataContract("material.reference")
