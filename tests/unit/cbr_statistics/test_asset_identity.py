"""Logical source assets remain distinct even when their original bytes agree."""
from dataclasses import replace
from datetime import date
from io import BytesIO
import json

import pytest
from openpyxl import Workbook

from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.tables.statistics.readable import readable_workbook
from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot, flake_from_snapshot
from stratbox.domains.cbr.tables.statistics.validation import compare_workbook_flakes
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot, dataset_from_snapshot, inputs_from
from stratbox.domains.cbr.products.statistics.views import build_view, view_from_snapshot


SERIES = "cbr.monetary_statistics.monetary_agg"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def originals():
    book = Workbook()
    book.active.title = "Денежные агрегаты"
    book.active.append(["Amount, млн руб.", date(2026, 1, 1)])
    book.active.append(["Total", 123])
    buffer = BytesIO()
    book.save(buffer)
    payload = SourcePayload(buffer.getvalue(), XLSX, SERIES)
    # Shared byte evidence is deliberate: the logical asset is an independent
    # coordinate and must change identity even with this identical lineage.
    receipt = UsedInputReceipt("original", ByteIdentity.of(payload.data), XLSX, "inline", SERIES)
    return tuple(IdentifiedOriginal(SourceAssetIdentity(SERIES, "capture-1", asset), payload, "xlsx",
                                   lineage=(receipt,)) for asset in ("main", "appendix"))


def test_same_bytes_under_two_assets_have_distinct_flakes_and_exact_input_vectors(originals):
    flakes = tuple(extract_workbook_value(original) for original in originals)
    assert flakes[0].source_identity == flakes[1].source_identity
    assert flakes[0].lineage == flakes[1].lineage
    assert [flake.asset_id for flake in flakes] == ["main", "appendix"]
    assert flakes[0].identity != flakes[1].identity
    for flake in flakes:
        snapshot = flake_snapshot(flake)
        assert flake_from_snapshot(snapshot) == flake
        meta = dict(zip((column.name for column in snapshot.table("metadata").schema.columns),
                        snapshot.table("metadata").rows[0]))
        assert meta["asset_id"] == flake.asset_id
        assert json.loads(readable_workbook(flake).data.splitlines()[0])["asset_id"] == flake.asset_id
    dataset = align_statistics(flakes, strict=True)
    assert tuple(item.asset_id for item in dataset.inputs) == ("main", "appendix")
    assert tuple(item.flake for item in dataset.inputs) == tuple(flake.identity for flake in flakes)
    restored = dataset_from_snapshot(dataset_snapshot(dataset))
    assert restored == dataset
    assert {dict(item.dimensions)["source_asset_id"] for batch in restored.batches for item in batch.observations} == {"main", "appendix"}
    assert len({item.subject for batch in restored.batches for item in batch.observations}) == 2
    assert len({item.metric.id for batch in restored.batches for item in batch.observations}) == 2
    view = view_from_snapshot(build_view(restored).snapshot)
    assert inputs_from(view.snapshot.table("inputs")) == dataset.inputs
    with pytest.raises(ValueError, match="comparison_asset_mismatch"):
        compare_workbook_flakes(*flakes)


def test_asset_scoped_original_lineage_is_admitted(originals):
    original = originals[1]
    receipt = replace(original.lineage[0], source_id=original.asset.source_id)
    flake = extract_workbook_value(replace(original, lineage=(receipt,)))
    assert flake_from_snapshot(flake_snapshot(flake)) == flake


@pytest.mark.parametrize("asset_id", ["", "invalid/asset", "invalid asset"])
def test_retained_flakes_and_input_versions_validate_logical_asset_tokens(originals, asset_id):
    flake = extract_workbook_value(originals[0])
    with pytest.raises(ValueError, match="source.identity_token_invalid"):
        flake_snapshot(replace(flake, asset_id=asset_id))
    snapshot = flake_snapshot(flake)
    metadata = snapshot.table("metadata")
    index = tuple(column.name for column in metadata.schema.columns).index("asset_id")
    row = list(metadata.rows[0]); row[index] = asset_id
    tables = tuple((name, TypedTable(metadata.schema, (tuple(row),)) if name == "metadata" else table)
                   for name, table in snapshot.tables)
    forged = DatasetSnapshot.build(snapshot.manifest.dataset_id, "forged", snapshot.manifest.contract, tables,
                                   coverage=snapshot.manifest.coverage, inputs=snapshot.manifest.inputs)
    with pytest.raises(ValueError, match="source.identity_token_invalid"):
        flake_from_snapshot(forged)
    dataset = align_statistics((flake,))
    invalid = replace(dataset, inputs=(replace(dataset.inputs[0], asset_id=asset_id),))
    with pytest.raises(ValueError, match="source.identity_token_invalid"):
        dataset_snapshot(invalid)
    inputs = dataset_snapshot(dataset).table("inputs")
    index = tuple(column.name for column in inputs.schema.columns).index("asset_id")
    row = list(inputs.rows[0]); row[index] = asset_id
    with pytest.raises(ValueError, match="source.identity_token_invalid"):
        inputs_from(TypedTable(inputs.schema, (tuple(row),)))
