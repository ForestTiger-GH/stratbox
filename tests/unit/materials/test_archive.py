from io import BytesIO
from zipfile import ZipFile

import pytest

from stratbox.core.execution import ExecutionContext
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.materials.definitions import ReadLocationRequest
from stratbox.core.operations.materials.operations import read_location
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.evidence import SourcePayload


def test_archive_can_collect_members_from_distinct_named_stores_and_supplied_bytes(tmp_path):
    a, b, out = (LocalFileStore(str(tmp_path / name)) for name in ("a", "b", "out"))
    a.write_bytes("report", b"%PDF-1.7\nexact source")
    b.write_bytes("report", b"opaque workbook")
    left = read_location(ReadLocationRequest("report", "application/pdf"), store=a).value.material
    right = read_location(ReadLocationRequest("report"), store=b).value.material
    context = ExecutionContext(bindings=tuple(
        ProviderBinding(name, CapabilityRequirement(role), "ready", store)
        for name, role, store in (("a", "filestore", a), ("b", "filestore", b), ("out", "output_filestore", out))))
    result = archive_materials(ArchiveRequest((
        ArchiveMember("source.pdf", left, ProviderSelection("a")),
        ArchiveMember("report.xlsx", right, ProviderSelection("b")),
        ArchiveMember("description.txt", SourcePayload(b"source selection", "text/plain")),
    ), OriginalDestination("bundle.zip")), output_selection=ProviderSelection("out"), context=context)
    assert result.outcome == "succeeded", result.diagnostics
    with ZipFile(BytesIO(out.read_bytes("bundle.zip"))) as archive:
        assert archive.read("source.pdf") == a.read_bytes("report")
        assert archive.read("report.xlsx") == b.read_bytes("report")
        assert archive.read("description.txt") == b"source selection"
    assert result.value.material.identity not in {left.identity, right.identity}
    assert all(receipt.container == result.value.material.identity and receipt.member == name
               for name, receipt in result.value.members)
    assert len(result.used_inputs) == 3


@pytest.mark.parametrize("names", [("../unsafe",), ("same", "SAME")])
def test_unsafe_or_colliding_archive_members_do_not_write(tmp_path, names):
    out = LocalFileStore(str(tmp_path))
    result = archive_materials(ArchiveRequest(tuple(ArchiveMember(name, SourcePayload(b"data")) for name in names),
                                             OriginalDestination("archive.zip")), output_store=out)
    assert result.outcome == "failed" and not result.effects and not out.exists("archive.zip")
