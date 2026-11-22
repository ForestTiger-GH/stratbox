"""Logical archive membership survives different stores and packaging methods."""
from io import BytesIO
from zipfile import ZipFile

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains import frank_rg as frg
from stratbox.shared.data.processing import DataRole
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.material_collections import decode_collection


_NAME = "2026-05-01_Экспресс выдачи.xlsx"


def _plan(path):
    path.mkdir()
    (path / _NAME).write_bytes(b"unaltered publisher workbook bytes")
    store = LocalFileStore(str(path))
    result = frg.plan_cleanup(frg.PlanCleanupRequest("."), store=store)
    assert result.outcome == "succeeded", result.diagnostics
    return store, result.value


def _manifest(data):
    with ZipFile(BytesIO(data)) as package:
        manifest = decode_collection(package.read("manifest.json"))
        assert {member.name for member in manifest.members} == set(package.namelist()) - {"manifest.json"}
        for member in manifest.members:
            assert ByteIdentity.of(package.read(member.name)) == member.identity
        assert package.read(_NAME) == b"unaltered publisher workbook bytes"
    return manifest


def test_memory_and_stream_archives_share_location_independent_original_manifest(tmp_path):
    first, first_plan = _plan(tmp_path / "first")
    second, second_plan = _plan(tmp_path / "second")
    memory = frg.prepare_archive(first_plan, store=first)
    assert memory.outcome == "succeeded", memory.diagnostics
    output = LocalFileStore(str(tmp_path))
    streamed = frg.prepare_archive_to_store(frg.StreamArchiveRequest(second_plan, "output.zip"),
        store=second, output_store=output)
    assert streamed.outcome == "succeeded", streamed.diagnostics
    a = _manifest(memory.value.data)
    b = _manifest((tmp_path / "output.zip").read_bytes())
    assert a.identity == b.identity
    assert a.complete and a.coverage.status == "complete"
    member, = a.members
    assert member.contract.role is DataRole.ORIGINALS
    assert member.source_asset.series_id == "frg.express.issuance"
    assert member.source_asset.issue_id == "2026-05-01"
    assert member.source_asset.asset_id == "xlsx"
    assert a.inputs[0].source_id == "frg.express.issuance"


def test_selection_report_remains_a_separate_manifested_supplement(tmp_path):
    store, plan = _plan(tmp_path / "inputs")
    result = frg.prepare_archive_to_store(frg.StreamArchiveRequest(plan, "with-report.zip", b'{"selected":1}'),
        store=store, output_store=LocalFileStore(str(tmp_path)))
    assert result.outcome == "succeeded", result.diagnostics
    data = (tmp_path / "with-report.zip").read_bytes()
    manifest = _manifest(data)
    report = next(member for member in manifest.members if member.key == "selection_report")
    assert report.contract.role is None
    assert report.source_asset is None
    assert report.identity == ByteIdentity.of(b'{"selected":1}')
    with ZipFile(BytesIO(data)) as package:
        assert package.read("selection_report.json") == b'{"selected":1}'
