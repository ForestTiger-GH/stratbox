"""Streaming FRG archive tests: size, integrity, safe retry and exact plan."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from stratbox.base.filestore import LocalFileStore
from stratbox.macrobanks import frg

LATEST = "2026-05-01_Экспресс выдачи.xlsx"
OLDER = "2026-04-01_Экспресс выдачи.xlsx"


def _setup(tmp_path, large=False):
    source = tmp_path / "inputs"
    source.mkdir()
    latest = source / LATEST
    if large:
        with latest.open("wb") as stream:
            stream.truncate(105 * 1024 * 1024)  # > old 100 MiB aggregate / 32 MiB member ceilings
    else:
        latest.write_bytes(b"latest")
    (source / OLDER).write_bytes(b"older")
    output = tmp_path / "outputs"
    output.mkdir()
    input_store = LocalFileStore(root=str(source))
    output_store = LocalFileStore(root=str(output))
    plan_result = frg.plan_cleanup(
        frg.PlanCleanupRequest(".", delete_others=False), store=input_store
    )
    assert plan_result.outcome == "succeeded", plan_result.diagnostics
    return input_store, output_store, plan_result.value, latest, output


def test_large_frg_archive_streams_to_disk_with_report(tmp_path):
    inp, out, plan, latest, destination_dir = _setup(tmp_path, large=True)
    result = frg.prepare_archive_to_store(
        frg.StreamArchiveRequest(plan, "frg-latest.zip", b'{"status":"complete"}'),
        store=inp,
        output_store=out,
    )
    assert result.outcome == "succeeded", result.diagnostics
    receipt = result.value
    assert receipt.identity.size > 100 * 1024 * 1024
    data = destination_dir / "frg-latest.zip"
    assert data.exists()
    expected = next(action.destination.split("/")[-1] for action in plan.actions if action.kind != "remove")
    with ZipFile(data) as package:
        assert set(package.namelist()) == {expected, "selection_report.json"}
        assert package.getinfo(expected).file_size == 35 * 1024 * 1024
        assert package.read("selection_report.json") == b'{"status":"complete"}'
    digest = sha256()
    with data.open("rb") as raw:
        while chunk := raw.read(1024 * 1024):
            digest.update(chunk)
    assert digest.hexdigest() == receipt.identity.sha256
    assert latest.stat().st_size == 35 * 1024 * 1024


def test_changed_source_blocks_archive_and_preserves_existing_output(tmp_path):
    inp, out, plan, latest, destination_dir = _setup(tmp_path)
    target = destination_dir / "frg-latest.zip"
    target.write_bytes(b"previous-safe-artifact")
    latest.write_bytes(b"changed-after-plan")
    result = frg.prepare_archive_to_store(
        frg.StreamArchiveRequest(plan, "frg-latest.zip"),
        store=inp, output_store=out,
    )
    assert result.outcome == "failed"
    assert target.read_bytes() == b"previous-safe-artifact"


def test_report_written_as_separate_archive_member(tmp_path):
    inp, out, plan, latest, destination_dir = _setup(tmp_path)
    result = frg.prepare_archive_to_store(
        frg.StreamArchiveRequest(plan, "bad.zip", b'{"hello":"world"}'),
        store=inp, output_store=out,
    )
    assert result.outcome == "succeeded", result.diagnostics
    assert (destination_dir / "bad.zip").exists()
