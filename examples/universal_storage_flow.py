"""Offline originals, readable artifacts and typed snapshots across two stores.

Run with Python 3.10+ and an installed stratbox; no optional dependencies needed.
All input bytes are synthetic. This example does not parse PDF or invoke AI.
"""
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from stratbox.core.operations.materials.definitions import (
    ArtifactDestination, ReadArtifactRequest, ReadLocationRequest, SaveArtifactRequest,
    TransferArtifactRequest,
)
from stratbox.core.operations.materials.operations import read_artifact, read_location, save_artifact, transfer_artifact
from stratbox.core.operations.source.original_definitions import OriginalDestination, SaveOriginalRequest
from stratbox.core.operations.source.originals import save_original
from stratbox.core.storage.datasets import FileDatasetStore, MemoryDatasetStore
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.materials import ArtifactReference, MaterialArtifact


def value(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def main():
    with TemporaryDirectory() as root:
        incoming = LocalFileStore(str(Path(root) / "incoming"))
        retained = LocalFileStore(str(Path(root) / "retained"))
        incoming.write_bytes("report.pdf", b"%PDF-1.7\nsynthetic original\n%%EOF")
        original = value(read_location(ReadLocationRequest("report.pdf", "application/pdf", "sample.report"), store=incoming))
        saved_original = value(save_original(SaveOriginalRequest(original.payload, OriginalDestination("originals/report.pdf")), store=retained))
        assert saved_original.material.identity == original.payload.identity

        readable = MaterialArtifact(DataContract("sample.readable", 1, DataRole.READABLE),
            Representation("sample.markdown", 1, "text/markdown", b"# Supplied conversion result\n", "utf-8"),
            (UsedInputReceipt.for_payload(original.payload, "original_pdf"),), "sample.report")
        saved = value(save_artifact(SaveArtifactRequest(readable, ArtifactDestination("readable/report.md")), store=incoming))
        reference = ArtifactReference.from_bytes(saved.artifact.to_bytes())
        copied = value(transfer_artifact(TransferArtifactRequest(reference, ArtifactDestination("readable/report.md")),
                                        source_store=incoming, output_store=retained))
        assert value(read_artifact(ReadArtifactRequest(copied.artifact), store=retained)) == readable

        contract = DataContract("sample.indicators", 1, DataRole.INTEGRATED)
        schema = TableSchema(contract, (ColumnSchema("period", ScalarType.TEXT),
            ColumnSchema("value", ScalarType.DECIMAL, nullable=True, unit="reported_units")), ("period",))
        table = TypedTable(schema, (("2026-09", Decimal("12.3400")), ("2026-10", None)))
        snapshot = DatasetSnapshot.build("sample.indicators", "v1", contract, (("values", table),),
                                         coverage=SnapshotCoverage("partial", "Two demonstration periods."))
        stores = (MemoryDatasetStore(provider_id="memory", scope_id="demo"),
                  FileDatasetStore(retained, "database", provider_id="files", scope_id="demo"))
        for store in stores:
            receipt = value(write_snapshot(WriteSnapshotRequest(snapshot), store=store))
            restored = value(read_snapshot(ReadSnapshotRequest(receipt.reference), store=store))
            assert restored == snapshot
        print("Verified PDF preservation, readable artifact replay and equal typed snapshots across adapters.")


if __name__ == "__main__":
    main()
