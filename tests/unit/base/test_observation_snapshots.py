"""Exact observation semantics survive a generic dataset adapter and corruption checks."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
import pytest

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.filestore.local import LocalFileStore


def batch():
    subject=SubjectRef("source.legal_entity","00001")
    period=PeriodRef("interval",start=date(2026,1,1),end=date(2026,3,31))
    metric=MetricRef("source.metric","RUB","flow","edition.2026",Decimal("1000.00"))
    records=tuple(Observation(subject,metric,period,(("geography","001"),("scope","full")),"legal_entity",
        value,status,"sheet:1/row:"+str(i),raw) for i,(value,status,raw) in enumerate((
            (Decimal("1.2300"),"reported","0001.2300"),(0,"reported","0"),(None,"blank",""),
            (None,"withheld",None),("publisher text","reported","publisher text"),
        )))
    return ObservationBatch("logical.observations",7,"release.1",records,
        (UsedInputReceipt.for_payload(SourcePayload(b"source"),"exact_source"),))


def test_typed_batch_roundtrip_through_a_new_file_adapter_preserves_every_field(tmp_path):
    original=batch();snapshot=observation_snapshot(original,dataset_id="retained.batch",version_id="stored.1")
    store=FileDatasetStore(LocalFileStore(str(tmp_path)),"datasets",provider_id="files",scope_id="tests")
    write=datasets.write_snapshot(datasets.WriteSnapshotRequest(snapshot),store=store)
    assert write.outcome=="succeeded",write.diagnostics
    reopened=FileDatasetStore(LocalFileStore(str(tmp_path)),"datasets",provider_id="files",scope_id="tests")
    read=datasets.read_snapshot(datasets.ReadSnapshotRequest(write.value.reference),store=reopened)
    assert read.outcome=="succeeded",read.diagnostics
    restored=observations_from_snapshot(read.value)
    assert restored==original
    assert restored.schema_version==7 and restored.release_id=="release.1"
    assert restored.observations[0].value.as_tuple()==Decimal("1.2300").as_tuple()
    assert restored.observations[0].metric.scale.as_tuple()==Decimal("1000.00").as_tuple()
    assert type(restored.observations[1].value) is int
    assert restored.observations[2].raw_token==""
    assert restored.observations[3].raw_token is None


def test_rows_remain_ordered_and_duplicate_records_are_not_aggregated():
    original=batch();duplicated=replace(original,observations=(original.observations[0],)*2)
    assert observations_from_snapshot(observation_snapshot(duplicated))==duplicated


def test_snapshot_rejects_missing_components_and_hidden_scalar_channels():
    snapshot=observation_snapshot(batch())
    with pytest.raises(ValueError,match="snapshot_invalid"):
        observations_from_snapshot(replace(snapshot,tables=snapshot.tables[:1]))
    table=snapshot.table("observations");rows=list(table.rows);row=list(rows[0]);row[15]=1;rows[0]=tuple(row)
    changed=DatasetSnapshot.build(snapshot.manifest.dataset_id,snapshot.manifest.version_id,snapshot.manifest.contract,
        (("metadata",snapshot.table("metadata")),("observations",TypedTable(table.schema,tuple(rows)))),
        coverage=snapshot.manifest.coverage,inputs=snapshot.manifest.inputs)
    with pytest.raises(ValueError,match="value_encoding_invalid"):
        observations_from_snapshot(changed)


def test_empty_batches_preserve_metadata_and_lineage_without_invented_coverage():
    empty=replace(batch(),observations=())
    snapshot=observation_snapshot(empty)
    assert snapshot.manifest.coverage.status=="unknown"
    assert observations_from_snapshot(snapshot)==empty
