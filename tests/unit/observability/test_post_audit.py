"""Core post-audit counterexamples: lifecycle, generation proofs and bounded state."""
from dataclasses import replace
from datetime import datetime, timezone
import json
import pytest

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import PublicationReceipt
from stratbox.core.observability import (
    JournalRecord, CaptureCoverage, SequenceRange, FileJournalWriter,
    FileJournalReader, SegmentDescriptor, build_manifest, decode_manifest,
    build_operation_history, inspect_execution_lifecycle,
    assess_generation_coverage, RecordMemorySink, FileEventSink, BufferedFileJournal,
    CapturePolicy, PersistencePolicy, ObserverLimits, OriginClaim,
    fact_for_artifact, record_from_fact, project_artifact_state,
    fact_from_publication, project_source_state, RevisionResolution,
)

TIME = datetime(2026, 11, 15, tzinfo=timezone.utc)


def event(invocation, sequence, kind, *, operation="example.operation", record_id=None, payload=None):
    return JournalRecord(record_id or f"{invocation}_{sequence}_{kind}", "execution", kind, TIME,
                         payload or {}, invocation_id=invocation,
                         operation_id=operation, sequence=sequence,
                         outcome="succeeded" if kind == "operation.finished" else None)


def evidence(invocation, generation="G", last=3):
    return CaptureCoverage(invocation, "scope", last, (SequenceRange(1, last),),
                           terminal_seen=True, start_seen=True, generation_id=generation,
                           evidence_quality="collector_observed")


def complete_run(invocation):
    return (event(invocation, 1, "operation.started"),
            event(invocation, 2, "operation.stage"),
            event(invocation, 3, "operation.finished"))


def stored_manifest(tmp_path, records, coverages, generation="G"):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "events", writer_id="writer")
    batch = writer.write_batch(records)
    assert batch.state == "confirmed"
    manifest = build_manifest(writer_id="writer", generation_id=generation, scope_id="scope",
                              segments=(SegmentDescriptor.from_receipt(batch),), records=records,
                              sealed_at_utc=TIME, capture_evidence=coverages)
    receipt = writer.write_manifest(manifest)
    assert receipt.state == "confirmed"
    return manifest, FileJournalReader(store, namespace=writer.namespace).read_report(manifest_receipt=receipt)


@pytest.mark.parametrize("records,code", [
    ((event("A", 1, "operation.started"), event("A", 2, "operation.finished"),
      event("A", 3, "operation.stage")), "journal.finish_position_invalid"),
    ((event("A", 1, "operation.started"), event("A", 1, "operation.finished")),
     "journal.sequence_conflict"),
    ((event("A", 2, "operation.started"), event("A", 3, "operation.finished")),
     "journal.start_position_invalid"),
    ((event("A", 1, "operation.started"), event("A", 2, "operation.finished", operation="another.operation")),
     "journal.operation_identity_conflict"),
    ((event("A", 1, "operation.started", payload={"sequence": 99}),
      event("A", 2, "operation.finished")), "journal.execution_envelope_mismatch"),
])
def test_lifecycle_contradiction_never_complete(tmp_path, records, code):
    assert code in inspect_execution_lifecycle(records, "A").problems
    history = build_operation_history(records, "A", coverage=evidence("A", last=max(x.sequence for x in records)))
    assert history.coverage == "incomplete"
    assert code in history.problems
    manifest, report = stored_manifest(tmp_path, records, (evidence("A", last=max(x.sequence for x in records)),))
    assert manifest.seal_state == "incomplete"
    assert report.capture_coverage == "incomplete" and not report.complete


def test_identical_record_replay_is_idempotent(tmp_path):
    records = complete_run("A")
    history = build_operation_history((*records, records[0]), "A", coverage=evidence("A"))
    assert history.coverage == "complete" and "journal.sequence_conflict" not in history.problems
    assert inspect_execution_lifecycle((*records, records[0]), "A").structurally_valid


def test_start_missing_without_producer_evidence_is_unverified():
    history = build_operation_history((event("A", 3, "operation.finished"),), "A")
    assert history.coverage == "indeterminate"


def test_generation_two_independent_local_sequences_complete(tmp_path):
    records = (*complete_run("A"), *complete_run("B"))
    manifest, report = stored_manifest(tmp_path, records, (evidence("A"), evidence("B")))
    assert manifest.seal_state == "sealed"
    assert manifest.schema_version == 2
    assert manifest.capture_assessment.invocation_count == 2
    assert manifest.capture_assessment.complete_count == 2
    assert manifest.capture_assessment.total_missing_events == 0
    assert report.complete and report.capture_coverage == "complete"
    assert len(report.records) == 6


@pytest.mark.parametrize("invocations,coverage_ids", [
    (("A", "B"), ("A",)),
    (("A",), ("A", "B")),
])
def test_generation_requires_exact_observed_invocation_set(tmp_path, invocations, coverage_ids):
    records = tuple(r for inv in invocations for r in complete_run(inv))
    manifest, report = stored_manifest(tmp_path, records, tuple(evidence(x) for x in coverage_ids))
    assert manifest.capture_assessment.status == "incomplete"
    assert manifest.seal_state == "incomplete" and not report.complete
    assert report.capture_coverage == "incomplete"


def test_one_invalid_invocation_invalidates_generation(tmp_path):
    records = (*complete_run("A"), event("B", 1, "operation.started"),
               event("B", 2, "operation.finished"), event("B", 3, "operation.stage"))
    manifest, report = stored_manifest(tmp_path, records, (evidence("A"), evidence("B")))
    assert manifest.capture_assessment.incomplete_count == 1
    assert not report.complete
    assert len(report.records) == 6


def test_generation_id_explicit_mismatch_rejected(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "events", writer_id="writer")
    records = complete_run("A")
    receipt = writer.write_batch(records)
    with pytest.raises(ValueError, match="journal.generation_mismatch"):
        build_manifest(writer_id="writer", generation_id="G2", scope_id="scope",
                       segments=(SegmentDescriptor.from_receipt(receipt),),
                       records=records, sealed_at_utc=TIME,
                       capture_evidence=(evidence("A", "G1"),))


def test_generation_without_binding_remains_unsealed(tmp_path):
    records = complete_run("A")
    manifest, report = stored_manifest(tmp_path, records, (evidence("A", None),))
    assert manifest.seal_state == "incomplete"
    assert manifest.capture_assessment.status == "indeterminate"
    assert not report.complete


def test_manifest_v1_not_silently_promoted(tmp_path):
    records = complete_run("A")
    manifest, _ = stored_manifest(tmp_path, records, (evidence("A"),))
    from stratbox.core.observability import encode_manifest
    encoded = json.loads(encode_manifest(manifest))
    encoded["schema_version"] = 1
    with pytest.raises(ValueError, match="journal.unsupported_manifest_schema"):
        decode_manifest(json.dumps(encoded).encode())


def test_memory_metadata_invocations_and_finalization_are_bounded():
    sink = RecordMemorySink(CapturePolicy(max_records=1), limits=ObserverLimits(
        max_tracked_invocations=2, max_total_sequence_ranges=6, max_ranges_per_invocation=3))
    for i in range(500):
        sink.capture(event(f"inv{i}", 1, "operation.started"))
    health = sink.health_snapshot()
    assert health.tracked_invocations == 2
    assert health.metadata_overflow_events >= 498
    assert health.degraded and len(sink.records) == 1
    snapshot = sink.finalize_generation()
    assert snapshot.health.generation_finalized
    assert len(snapshot.invocation_ids) <= 2
    assert not sink.capture(event("too_late", 1, "operation.started"))
    assert sink.health_snapshot().degraded


def test_metadata_global_range_budget_is_bounded():
    sink = RecordMemorySink(CapturePolicy(max_records=100), limits=ObserverLimits(
        max_tracked_invocations=2, max_total_sequence_ranges=2, max_ranges_per_invocation=2))
    for n in (1, 3, 5, 7):
        sink.capture(event("A", n, "operation.stage"))
    assert sink.health_snapshot().tracked_sequence_ranges <= 2
    assert sink.health_snapshot().metadata_overflow_events >= 1
    cov = sink.coverage_for("A")
    assert cov.unknown_loss_count > 0 and cov.evidence_quality == "claimed"


def test_file_sink_origin_and_metadata_bounds(tmp_path):
    writer = FileJournalWriter(LocalFileStore(str(tmp_path)), "events", writer_id="writer")
    sink = FileEventSink(BufferedFileJournal(writer), origin=OriginClaim("producer", "collector", "G"),
                         limits=ObserverLimits(1, 4, 4))
    assert sink.capture(event("A", 1, "operation.started"))
    assert not sink.capture(event("B", 1, "operation.started"))
    assert sink.coverage_for("A").generation_id == "G"
    assert sink.health_snapshot().metadata_overflow_events == 1
    assert sink.finalize_generation().health.generation_finalized
    assert not sink.capture(event("A", 2, "operation.finished"))


def test_receipt_capacity_prevents_new_segment_and_allows_ack(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "buffer", writer_id="writer", policy=PersistencePolicy(max_buffer_records=1))
    journal = BufferedFileJournal(writer, max_retained_receipts=1)
    first = journal.append(event("A", 1, "operation.started"))
    assert first.state == "confirmed"
    with pytest.raises(ValueError, match="journal.receipt_capacity_exceeded"):
        journal.append(event("B", 1, "operation.started"))
    assert len(journal.pending) == 1
    assert len(journal.snapshot_receipts()) == 1
    assert not (tmp_path / writer.segment_path("some_new_id")).exists()
    assert journal.acknowledge_receipts((first.segment_id,)) == 1
    assert journal.flush().state == "confirmed"
    assert len(journal.receipts) == 1


def test_unknown_receipt_cannot_be_evicted_before_reconcile(tmp_path):
    store = LocalFileStore(str(tmp_path))
    class LostAck:
        def makedirs(self, p): return store.makedirs(p)
        def open_read(self, p): return store.open_read(p)
        def create_if_absent(self, p, data):
            store.create_if_absent(p, data)
            raise OSError("lost acknowledgement")
    bad = FileJournalWriter(LostAck(), "events", writer_id="writer",
                            policy=PersistencePolicy(max_buffer_records=1))
    journal = BufferedFileJournal(bad, max_retained_receipts=1)
    first = journal.append(event("A", 1, "operation.started"))
    assert first.state == "unknown"
    with pytest.raises(ValueError, match="journal.receipt_ack_unconfirmed"):
        journal.acknowledge_receipts((first.segment_id,))
    journal.writer = FileJournalWriter(store, "events", writer_id="writer",
                                       policy=PersistencePolicy(max_buffer_records=1))
    assert journal.reconcile_pending().state == "confirmed"
    assert len(journal.receipts) == 1


def test_artifact_version_projection_fully_scoped():
    def fact(version, content, stored):
        return record_from_fact(fact_for_artifact(artifact_id="A", version_id=version,
            identity=ByteIdentity.of(content), occurred_at_utc=TIME,
            stored=stored, receipt_status="stored" if stored else None))
    v1 = fact("v1", b"old", True)
    v2 = fact("v2", b"new", False)
    absent = project_artifact_state((v1,), "A", version_id="v2")
    assert not absent.produced and not absent.stored_confirmed and absent.identity_sha256 is None
    actual = project_artifact_state((v1, v2), "A", version_id="v2")
    assert actual.produced and not actual.stored_confirmed and not actual.conflicting_identity
    current = project_artifact_state((v1, v2), "A")
    assert current.indeterminate and current.identity_sha256 is None


def test_publication_revision_relation_requires_domain_authority():
    a = PublicationReceipt("source", "target", "release", "first", ByteIdentity.of(b"a"), "confirmed")
    b = PublicationReceipt("source", "target", "release", "second", ByteIdentity.of(b"b"), "confirmed")
    items = tuple(record_from_fact(fact_from_publication(x, occurred_at_utc=TIME)) for x in (a, b))
    unknown = project_source_state(items, "source")
    assert unknown.observed_byte_versions == 2 and unknown.revision_relation == "indeterminate"
    assert not unknown.conflict
    correction = project_source_state(items, "source", revision_resolver=lambda _: RevisionResolution("supersedes"))
    assert not correction.conflict and correction.revision_relation == "supersedes"
    competition = project_source_state(items, "source", revision_resolver=lambda _: RevisionResolution("competing"))
    assert competition.conflict and competition.revision_relation == "competing"


def test_filtered_event_after_finish_is_not_a_terminal_run():
    records = (event("A", 1, "operation.started"), event("A", 2, "operation.finished"))
    cov = CaptureCoverage("A", "scope", 3, (SequenceRange(1, 3),),
                          policy_excluded_ranges=(SequenceRange(3, 3),),
                          terminal_seen=True, start_seen=True, generation_id="G",
                          evidence_quality="collector_observed")
    history = build_operation_history(records, "A", coverage=cov)
    assert history.coverage == "incomplete"
    assert "journal.producer_tail_after_finish" in history.problems


def test_manifest_aggregate_revalidated_against_actual_records(tmp_path):
    records = (*complete_run("A"), *complete_run("B"))
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "events", writer_id="writer")
    batch = writer.write_batch(records)
    manifest = build_manifest(writer_id="writer", generation_id="G", scope_id="scope",
                              segments=(SegmentDescriptor.from_receipt(batch),), records=records,
                              sealed_at_utc=TIME, capture_evidence=(evidence("A"), evidence("B")))
    assert manifest.seal_state == "sealed"
    altered = replace(manifest.capture_assessment, total_unknown_losses=5)
    # A self-consistent manifest digest alone cannot make an incorrect
    # declared generation aggregate true. Reader must recompute it.
    from stratbox.core.observability.journal.manifests import JournalManifest, _data
    from stratbox.shared.data import canonical_manifest_bytes
    from hashlib import sha256
    provisional = object.__new__(JournalManifest)
    for name in manifest.__dataclass_fields__:
        object.__setattr__(provisional, name, altered if name == "capture_assessment" else getattr(manifest, name))
    digest = sha256(canonical_manifest_bytes(_data(provisional, include_id=False))).hexdigest()
    forged = replace(manifest, capture_assessment=altered, manifest_id=digest)
    receipt = writer.write_manifest(forged)
    report = FileJournalReader(store, namespace=writer.namespace).read_report(manifest_receipt=receipt)
    assert report.storage_coverage == "complete"
    assert report.capture_coverage == "incomplete"
    assert any(issue.code == "journal.generation_assessment_mismatch" for issue in report.issues)
    assert not report.complete


def test_partial_multi_invocation_generation_keeps_good_records(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "events", writer_id="writer")
    a, b = complete_run("A"), complete_run("B")
    r_a, r_b = writer.write_batch(a), writer.write_batch(b)
    manifest = build_manifest(writer_id="writer", generation_id="G", scope_id="scope",
        segments=tuple(SegmentDescriptor.from_receipt(x) for x in (r_a, r_b)),
        records=(*a, *b), sealed_at_utc=TIME, capture_evidence=(evidence("A"), evidence("B")))
    mr = writer.write_manifest(manifest)
    (tmp_path / r_b.locator).unlink()
    report = FileJournalReader(store, namespace=writer.namespace).read_report(manifest_receipt=mr)
    assert report.records == a
    assert report.storage_coverage == "incomplete" and not report.complete
    assert any(issue.code == "journal.segment_missing" for issue in report.issues)


def test_many_invocations_have_no_cross_run_sequence_merge():
    records = tuple(record for i in range(250) for record in complete_run(f"inv{i}"))
    all_evidence = tuple(evidence(f"inv{i}") for i in range(250))
    result = assess_generation_coverage(records, all_evidence, scope_id="scope", generation_id="G")
    assert result.status == "complete"
    assert result.invocation_count == result.complete_count == 250
    assert result.total_missing_events == 0
