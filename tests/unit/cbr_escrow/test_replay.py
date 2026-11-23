"""Cold-process continuation through each independent escrow material boundary."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.codec import reference_value
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations import project_finance as escrow
from stratbox.domains.cbr.tables.project_finance.profiles import required_indicators
from stratbox.domains.cbr.tables.project_finance.columns import resolve_indicator_spec_by_header
from stratbox.domains.cbr.products.project_finance.pivots import build_escrow_pivot
from stratbox.domains.cbr.integration.project_finance.snapshots import dataset_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.evidence import SourcePayload


def checked(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def publication(*, period="01062026", region="Example region", amount="0012.2500", extra=True):
    book = Workbook()
    sheet = book.active
    sheet.title = "Regions"
    specs = list(required_indicators())
    headers = [spec.canonical_name for spec in specs]
    values = [7.25 if spec.value_kind == "percent" else amount for spec in specs]
    if extra:
        headers.append("Unmapped source measure")
    sheet.append(["No.", "Субъект Российской Федерации (федеральный округ)", *headers])
    sheet.append(["Центральный ФО", None, *values, *(["not understood"] if extra else [])])
    region_values = list(values)
    region_values[0], region_values[1], region_values[2] = 0, None, "—"
    sheet.append([1, region, *region_values, *(["NA"] if extra else [])])
    sheet.append(["Итого", None, *values, *(["=1+1"] if extra else [])])
    buffer = BytesIO()
    book.save(buffer)
    book.close()
    return escrow.ParseEscrowRequest(SourcePayload(buffer.getvalue(), source_id="escrow-example"), f"escrow_{period}.xlsx")


def persist(snapshot, root):
    store = FileDatasetStore(LocalFileStore(root), "datasets", provider_id="files", scope_id="escrow")
    written = checked(write_snapshot(WriteSnapshotRequest(snapshot), store=store))
    return store, written.reference


def test_flake_and_dataset_replay_preserve_cells_periods_and_render_in_a_fresh_process(tmp_path):
    first = checked(escrow.parse(publication()))
    assert first.df_cells.loc[first.df_cells["raw_token"].eq("0012.2500"), "value"].iloc[0] == Decimal("12.2500")
    assert {"blank", "marker", "unparsed", "formula_unresolved", "numeric"} <= set(first.df_cells["status"])
    first_snapshot = checked(escrow.build_flake_snapshot(escrow.EscrowFlakeSnapshotRequest(first)))
    store, reference = persist(first_snapshot, tmp_path)
    loaded = checked(read_snapshot(ReadSnapshotRequest(reference), store=store))
    replayed = checked(escrow.read_flake_snapshot(escrow.ReadEscrowSnapshotRequest(loaded)))
    pd.testing.assert_frame_equal(first.df_cells, replayed.df_cells)
    assert replayed.original_identity == first.original_identity
    assert replayed.source_id == first.source_id
    assert replayed.unmapped_headers == ("Unmapped source measure",)
    assert checked(escrow.build_flake_snapshot(escrow.EscrowFlakeSnapshotRequest(replayed))).identity == first_snapshot.identity

    second = checked(escrow.parse(publication(period="01072026", region="New region")))
    dataset = checked(escrow.integrate_flakes(escrow.IntegrateEscrowRequest((replayed, second))))
    assert "Example region" in set(dataset.rows["Регион"])
    assert "New region" in set(dataset.rows["Регион"])
    snapshot = checked(escrow.build_dataset_snapshot(escrow.EscrowDatasetSnapshotRequest(dataset)))
    _, reference = persist(snapshot, tmp_path)
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps({"root": str(tmp_path), "reference": reference_value(reference)}))
    script = r'''
import json, sys
from pathlib import Path
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.codec import reference_from
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations import project_finance as escrow
info=json.loads(Path(sys.argv[1]).read_text())
store=FileDatasetStore(LocalFileStore(info["root"]),"datasets",provider_id="files",scope_id="escrow")
loaded=read_snapshot(ReadSnapshotRequest(reference_from(info["reference"])),store=store)
assert loaded.outcome == "succeeded", loaded.diagnostics
restored=escrow.read_dataset_snapshot(escrow.ReadEscrowSnapshotRequest(loaded.value))
assert restored.outcome == "succeeded", restored.diagnostics
views=escrow.build_views(escrow.BuildEscrowViewsRequest(restored.value))
assert views.outcome == "succeeded", views.diagnostics
assert "Example region" not in views.value.region_order
assert "Example region" in set(restored.value.rows["Регион"])
book=escrow.render_workbook(views.value)
assert book.outcome == "succeeded", book.diagnostics
Path(info["root"],"from_replay.xlsx").write_bytes(book.value.data)
'''
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
    completed = subprocess.run([sys.executable, "-c", script, str(request_file)], env=env, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    book = load_workbook(tmp_path / "from_replay.xlsx", data_only=True)
    assert book["ССПКДПФО"]["B5"].value == 7.25
    assert book["ССПКДПФО"]["B5"].number_format == "#,##0.00"
    book.close()


def test_prepared_view_replay_keeps_tokens_precision_and_dataset_identity(tmp_path):
    flake = checked(escrow.parse(publication()))
    dataset = checked(escrow.integrate_flakes(escrow.IntegrateEscrowRequest((flake,))))
    view = checked(escrow.build_views(escrow.BuildEscrowViewsRequest(dataset)))
    snapshot = checked(escrow.build_view_snapshot(escrow.EscrowViewSnapshotRequest(view)))
    store, reference = persist(snapshot, tmp_path)
    loaded = checked(read_snapshot(ReadSnapshotRequest(reference), store=store))
    restored = checked(escrow.read_view_snapshot(escrow.ReadEscrowSnapshotRequest(loaded)))
    assert restored.source_dataset == view.source_dataset
    assert restored.row_metadata == view.row_metadata
    assert restored.coverage == view.coverage
    for code in view.pivots:
        pd.testing.assert_frame_equal(view.pivots[code], restored.pivots[code])
    assert checked(escrow.render_workbook(restored)) == checked(escrow.render_workbook(view))
    assert any("—" in frame.values for frame in restored.pivots.values())


def test_duplicate_observations_are_never_averaged():
    frame = pd.DataFrame({"indicator_code": ["x", "x"], "Регион": ["r", "r"], "Дата": ["2026-01-01"] * 2, "Значение": [2, 10]})
    with pytest.raises(ValueError, match="duplicate_observation"):
        build_escrow_pivot(frame, "x", region_order=["r"], date_order=["2026-01-01"])
    flake = checked(escrow.parse(publication()))
    result = escrow.integrate_flakes(escrow.IntegrateEscrowRequest((flake, flake)))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "escrow.duplicate_release"


def test_selected_or_mutated_material_cannot_be_admitted_as_a_complete_flake():
    flake = checked(escrow.parse(publication()))
    snapshot = checked(escrow.build_flake_snapshot(escrow.EscrowFlakeSnapshotRequest(flake)))
    partial = DatasetSnapshot(snapshot.manifest, snapshot.tables[:-1])
    result = escrow.read_flake_snapshot(escrow.ReadEscrowSnapshotRequest(partial))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "escrow.snapshot_invalid"
    flake.df_cells.loc[0, "raw_token"] = "modified"
    result = escrow.integrate_flakes(escrow.IntegrateEscrowRequest((flake,)))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "input.identity_mismatch"


def test_coverage_and_average_rate_have_distinct_semantic_identity():
    weighted = resolve_indicator_spec_by_header("Средневзвешенная ставка по кредитным договорам по федеральному округу, %")
    average = resolve_indicator_spec_by_header("Средняя ставка по кредитным договорам по федеральному округу, %")
    assert average.code != weighted.code
    flake = checked(escrow.parse(publication()))
    dataset = checked(escrow.integrate_flakes(escrow.IntegrateEscrowRequest((flake,))))
    different = replace(dataset, coverage=SnapshotCoverage("partial", "Caller selected one issue from a larger inventory."))
    assert dataset_snapshot(dataset).identity != dataset_snapshot(different).identity
    assert dataset_snapshot(dataset).manifest.version_id != dataset_snapshot(different).manifest.version_id


def test_prepared_escrow_views_retain_each_actual_publication_coordinate():
    first = checked(escrow.parse(publication()))
    second = checked(escrow.parse(publication(period="01072026")))
    dataset = checked(escrow.integrate_flakes(escrow.IntegrateEscrowRequest((first, second))))
    view = checked(escrow.build_views(escrow.BuildEscrowViewsRequest(dataset)))
    assert len(view.source_uses) == 2
    assert {use.coordinate.source_id for use in view.source_uses} == {"cbr.project_finance.escrow"}
    assert {use.coordinate.issue_id for use in view.source_uses} == {"2026-06-01", "2026-07-01"}
    saved = checked(escrow.build_view_snapshot(escrow.EscrowViewSnapshotRequest(view)))
    restored = checked(escrow.read_view_snapshot(escrow.ReadEscrowSnapshotRequest(saved)))
    assert restored.source_uses == view.source_uses
