"""End-to-end tests using real stratbox execution, receipts and LocalFileStore.

These tests require the *installed repository*, not the lightweight local stub.
No HTTP calls or external source state are involved.
"""
from datetime import datetime, timezone

from stratbox.base.filestore import LocalFileStore
from stratbox.data import ByteIdentity, SourcePayload, UsedInputReceipt
from stratbox.execution import ExecutionContext, OperationDefinition, run
from stratbox.execution.originals import OriginalDestination, SaveOriginalRequest, save_original
from stratbox.observability import (
    CapturePolicy, RecordMemorySink, FileJournalWriter, FileJournalReader,
    capture_operation_result, build_operation_history, assess_coverage,
    SegmentDescriptor, build_manifest, project_effect_state, record_from_result,
)

TIME = datetime(2026, 11, 15, tzinfo=timezone.utc)


def test_real_original_save_stored_receipt_and_complete_generation(tmp_path):
    source = SourcePayload(b"CBR sample source bytes", source_id="cbr_offices")
    request = SaveOriginalRequest(source, OriginalDestination("input/original.bin", mode="immutable"))
    plain = save_original(request, store=LocalFileStore(str(tmp_path / "plain")))
    collector = RecordMemorySink(CapturePolicy(progress=False))
    observed = save_original(request, store=LocalFileStore(str(tmp_path / "observed")),
                             context=ExecutionContext(sink=collector))
    assert plain.outcome == observed.outcome == "succeeded"
    assert plain.value.storage.identity == observed.value.storage.identity == source.identity
    assert plain.value.storage.status == observed.value.storage.status == "stored"
    assert plain.value.material.identity == observed.value.material.identity

    capture = capture_operation_result(observed, collector, occurred_at_utc=TIME)
    assert capture.produced >= 2 and capture.accepted == capture.produced
    records = collector.records
    effect_id = observed.effects[0].effect_id
    assert effect_id
    assert project_effect_state(records, effect_id).states == ("confirmed",)
    coverage = collector.coverage_for(observed.invocation_id, producer=observed.observability)
    history = build_operation_history(records, observed.invocation_id, coverage=coverage)
    assert history.coverage == "complete"

    store = LocalFileStore(str(tmp_path / "logs"))
    writer = FileJournalWriter(store, "journal", writer_id="test_writer")
    batch = writer.write_batch(records)
    assert batch.state == "confirmed"
    assessment = assess_coverage((r.sequence for r in records if r.record_type == "execution"),
                                 coverage, start_seen=True, terminal_seen=True)
    manifest = build_manifest(writer_id="test_writer", generation_id="generation_one",
                              scope_id=coverage.scope_id,
                              segments=(SegmentDescriptor.from_receipt(batch),),
                              assessment=assessment, sealed_at_utc=TIME,
                              capture_evidence=(coverage,))
    manifest_receipt = writer.write_manifest(manifest)
    assert manifest_receipt.state == "confirmed"
    reader = FileJournalReader(store, namespace=writer.namespace)
    recovered = reader.read_report(manifest_receipt=manifest_receipt)
    assert recovered.complete
    assert recovered.records == records
    assert project_effect_state(recovered.records, effect_id).states == ("confirmed",)


def test_real_computation_receipt_is_logged_without_raw_output():
    definition = OperationDefinition("test.compute_snapshot", 1, "small-math-v1", bytes, bytes)
    source = b"123"
    def work(request, invocation):
        invocation.stage("sum_values")
        invocation.use(UsedInputReceipt("input", ByteIdentity.of(request), "application/octet-stream", "inline"))
        output = str(sum(int(chr(x)) for x in request)).encode()
        invocation.record(ByteIdentity.of(output), parameters={"method": "sum"})
        return output

    plain = run(definition, source, work)
    recorder = RecordMemorySink()
    observed = run(definition, source, work, context=ExecutionContext(sink=recorder))
    assert plain.outcome == observed.outcome == "succeeded"
    assert plain.value == observed.value == b"6"
    assert observed.computation is not None
    summary = record_from_result(observed, occurred_at_utc=TIME, observation_id="sample")
    assert summary.payload["computation"]["output"]["sha256"] == ByteIdentity.of(b"6").sha256
    assert summary.payload["inputs"][0]["identity"]["sha256"] == ByteIdentity.of(source).sha256
    assert "123" not in str(summary.payload)
