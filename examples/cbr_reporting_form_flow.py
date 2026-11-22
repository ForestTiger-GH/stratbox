"""Offline CBR original -> DBF flakes -> durable snapshot -> CSV collection.

Run from a checkout with PYTHONPATH=src, or install stratbox[dataframe].
All inputs are synthetic; the example performs no HTTP or external publication.
The temporary directories stand for independently chosen input/output stores.
"""
from datetime import date
import json
from pathlib import Path
from struct import pack_into
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from stratbox.core.formats.archives.members import zip_bytes
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.materials.definitions import (
    ArtifactDestination, ReadLocationRequest, SaveArtifactRequest,
)
from stratbox.core.operations.materials.operations import read_location, save_artifact
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.codec import reference_from, reference_value
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr import reporting_forms as forms
from stratbox.domains.cbr.file_collection import CollectMaterial, CollectMaterialsRequest, collect_materials
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.material_collections import decode_collection


def accepted(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def demo_dbf():
    """Two classic text DBF records, including a retained deleted record."""
    fields = (("CODE", "C", 6, 0), ("VALUE", "N", 14, 4))
    header = bytearray(33 + 32 * len(fields))
    header[:4] = bytes((0x03, 126, 10, 1))
    width = 1 + sum(field[2] for field in fields)
    pack_into("<IHH", header, 4, 2, len(header), width)
    for index, (name, kind, length, decimals) in enumerate(fields):
        offset = 32 + index * 32
        header[offset:offset + len(name)] = name.encode("ascii")
        header[offset + 11] = ord(kind)
        header[offset + 16:offset + 18] = bytes((length, decimals))
    header[-1] = 0x0D
    records = b"".join(flag + code.ljust(6) + amount.rjust(14) for flag, code, amount in (
        (b" ", b"0012", b"000001.2300"), (b"*", b"0013", b""),
    ))
    return bytes(header) + records + b"\x1a"


def main():
    with TemporaryDirectory() as directory:
        incoming = LocalFileStore(str(Path(directory) / "incoming"))
        retained_root = str(Path(directory) / "retained")
        retained = LocalFileStore(retained_root)
        original_bytes = zip_bytes({"nested/A.dbf": demo_dbf(), "readme.txt": b"Synthetic source evidence."})
        incoming.write_bytes("delivery.bin", original_bytes)
        loaded = accepted(read_location(ReadLocationRequest("delivery.bin", "application/zip"), store=incoming))
        collection = accepted(collect_materials(CollectMaterialsRequest((
            CollectMaterial("form803", "cbr.reporting_forms.f803", "2026-10-01", "zip", payload=loaded.payload),
        ))))
        original = collection.originals[0][1]
        retained_original = accepted(save_artifact(SaveArtifactRequest(original.artifact,
            ArtifactDestination("originals/form803.zip")), store=retained))
        assert retained_original.artifact.material.identity == original.payload.identity

        flakes = accepted(forms.extract_forms(forms.ExtractFormRequest(
            forms.FormKey("803", date(2026, 10, 1)), original.payload)))
        assert flakes.members[0].table.records[0].values == ("0012", "000001.2300")
        assert flakes.members[0].table.records[1].deleted
        snapshot = accepted(forms.flake_snapshot(forms.FormFlakeSnapshotRequest(
            flakes, "demo.cbr.form803", "2026-10-01")))
        store = FileDatasetStore(retained, "datasets", provider_id="files", scope_id="demo")
        receipt = accepted(write_snapshot(WriteSnapshotRequest(snapshot), store=store))
        wire = json.dumps(reference_value(receipt.reference))

        # A new process can reconstruct this adapter and read the portable reference.
        reopened = FileDatasetStore(LocalFileStore(retained_root), "datasets", provider_id="files", scope_id="demo")
        snapshot_read = accepted(read_snapshot(ReadSnapshotRequest(reference_from(json.loads(wire))), store=reopened))
        restored = accepted(forms.restore_flakes(snapshot_read))
        assert restored == flakes
        exported = accepted(forms.render_flakes(forms.RenderFormFlakesRequest(
            restored, "regulatory-reporting/2026/2026-10-01/form-0409803")))
        payloads = tuple((name, SourcePayload(value.data, value.media_type, charset=value.encoding))
                         for name, value in exported.files)
        packed = accepted(archive_materials(ArchiveRequest(
            tuple(ArchiveMember(name, payload) for name, payload in payloads),
            OriginalDestination("exports/forms.zip"), manifest=exported.manifest), output_store=retained))
        with ZipFile(Path(retained_root) / "exports/forms.zip") as archive:
            manifest = decode_collection(archive.read("manifest.json"))
            assert manifest.identity == exported.manifest.identity
            assert set(archive.namelist()) == {member.name for member in manifest.members} | {"manifest.json"}
            restored_payloads = tuple((member.name, SourcePayload(archive.read(member.name), member.media_type))
                                      for member in manifest.members)
        resumed = accepted(forms.read_flake_export(forms.ReadFormFlakeExportRequest(restored_payloads, manifest)))
        assert resumed == flakes and packed.manifest.complete
        print("Verified exact original preservation, durable DBF flake replay and a complete CSV collection archive.")


if __name__ == "__main__":
    main()
