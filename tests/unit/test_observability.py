"""Universal observability: contracts, round-trips, history and fault-injected storage."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
import pytest

from stratbox.base.filestore.local import LocalFileStore
from stratbox.data import ByteIdentity, Comparison
from stratbox.execution import (Correlation, ExecutionContext, OperationDefinition,
                                InMemorySink, run)
from stratbox.observability import (
    BufferedFileJournal, CapturePolicy, CompositeEventSink, DomainFact,
    FileJournalReader, FileJournalWriter, JournalBarrierError, JournalDecodeError,
    JournalRecord, ObjectRef, PersistencePolicy, RecordFilter, RecordMemorySink,
    RequiredJournalGate, build_operation_history, decode_records, encode_records,
    export_projection_csv, fact_from_comparison, group_records, inspect_causes,
    make_fact_id, operation_state_from_result, project_dataset_state,
    project_effect_state, project_operation_state, projection_rows,
    record_from_fact, record_from_result, reconcile_write, select_records,
)

UTC = datetime(2026, 11, 14, tzinfo=timezone.utc)


def diagnostic_record(index=1, payload=None):
    return JournalRecord(f"diagnostic{index}", "diagnostic", "validation.issue_detected", UTC,
                         payload if payload is not None else {"code": "source.content_invalid"})


def execute(sink=None):
    spec = OperationDefinition("test.observed", 1, "method-1", str, str)
    def work(value, invocation):
        invocation.stage("parse")
        invocation.progress(1, 1)
        return value.upper()
    return run(spec, "ok", work, context=ExecutionContext(sink=sink))


def test_disabled_and_memory_preserve_business_semantics():
    baseline = execute()
    memory = RecordMemorySink(CapturePolicy(progress=False))
    observed = execute(memory)
    assert baseline.value == observed.value == "OK"
    assert baseline.outcome == observed.outcome == "succeeded"
    assert [x.kind for x in memory.records] == ["operation.started", "operation.stage", "operation.finished"]
    assert not baseline.observability.degraded
    memory.capture_result(observed, occurred_at_utc=UTC)
    summary = memory.records[-1]
    assert summary.record_type == "result_summary"
    assert summary.payload["observability"]["dropped"] == 0
    assert "value" not in summary.payload
    assert operation_state_from_result(observed).outcome == "succeeded"


def test_failed_sink_and_composite_isolation():
    class Broken:
        def emit(self, event):
            raise RuntimeError("network error")
    sink = RecordMemorySink()
    fanout = CompositeEventSink(Broken(), sink)
    result = execute(fanout)
    assert result.outcome == "succeeded"
    assert fanout.dropped >= 2
    assert len(sink.records) == 3
    assert execute(Broken()).observability.dropped >= 2


def test_capped_memory_capture_accounts_own_loss():
    sink = RecordMemorySink(CapturePolicy(max_records=1))
    execute(sink)
    assert len(sink.records) == 1
    assert sink.dropped == 2  # excluding progress


def test_domain_identity_separates_observations():
    subject = ObjectRef("dataset", "offices")
    key = make_fact_id("dataset.comparison_completed", subject, {"old": "a", "new": "b"})
    other = make_fact_id("dataset.comparison_completed", subject, {"old": "a", "new": "c"})
    assert key != other
    first = record_from_fact(DomainFact("dataset.comparison_completed", subject, key, UTC,
                                        {"value": Decimal("12.001")}), invocation_id="first")
    second = record_from_fact(DomainFact("dataset.comparison_completed", subject, key, UTC,
                                         {"value": Decimal("12.001")}), invocation_id="second")
    assert first.fact_id == second.fact_id
    assert first.record_id != second.record_id
    assert first.invocation_id != second.invocation_id


def test_round_trip_json_jsonl_and_exact_scalars():
    source = diagnostic_record(payload={"decimal": Decimal("1.000000000000000001"),
                                        "long_integer": 2**64, "empty": "", "zero": 0,
                                        "missing_like": None, "russian": "Привет"})
    for fmt in ("json", "jsonl"):
        decoded, = decode_records(encode_records((source,), format=fmt), format=fmt)
        assert decoded == source
        assert type(decoded.payload["decimal"]) is Decimal
        assert decoded.payload["long_integer"] == 2**64
        assert decoded.payload["empty"] == ""
        assert decoded.payload["zero"] == 0
        assert decoded.payload["missing_like"] is None
        assert "absent" not in decoded.payload
    assert decode_records(b"", format="jsonl") == ()
    assert decode_records(b"[]", format="json") == ()


def test_bad_version_utc_and_bad_line():
    with pytest.raises(ValueError):
        diagnostic_record().occurred_at_utc.replace(tzinfo=None) and JournalRecord(
            "bad", "diagnostic", "test.bad", datetime(2026, 11, 14), {})
    with pytest.raises(JournalDecodeError):
        decode_records(b'not-json\n')
    doc = json.loads(encode_records((diagnostic_record(),), format="json"))
    doc[0]["schema_version"] = 99
    with pytest.raises(JournalDecodeError):
        decode_records(json.dumps(doc).encode(), format="json")
    with pytest.raises(JournalDecodeError) as exc:
        decode_records(encode_records((diagnostic_record(),)) + b'{broken\n')
    assert exc.value.line == 2


def test_execution_history_and_filters():
    captured = RecordMemorySink(CapturePolicy(progress=True))
    result = execute(captured)
    records = captured.records
    history = build_operation_history(records, result.invocation_id, capture_complete=True)
    assert history.coverage == "complete"
    assert history.outcome == "succeeded"
    assert project_operation_state(records, result.invocation_id, capture_complete=True).stage == "parse"
    assert list(select_records(records, RecordFilter(invocation_id=result.invocation_id))) == list(records)
    assert len(list(select_records(records, RecordFilter(kinds=frozenset({"operation.finished"}))))) == 1
    assert len(group_records(records, lambda x: x.invocation_id)) == 1
    missing = build_operation_history(records[:-1], result.invocation_id, capture_complete=True)
    assert missing.coverage == "incomplete"
    assert "journal.finish_missing" in missing.problems
    assert build_operation_history(records, result.invocation_id).coverage == "indeterminate"
    assert inspect_causes(records, records[0].record_id).missing_parent_ids == ()


def test_domain_comparison_does_not_infer_revision():
    fact = fact_from_comparison(Comparison("indeterminate", "baseline.unavailable"),
                                dataset_id="regional_sme", baseline_id=None,
                                candidate_id="2026-11", occurred_at_utc=UTC)
    assert fact.kind == "dataset.comparison_completed"
    record = record_from_fact(fact)
    state = project_dataset_state((record,), "regional_sme")
    assert state.indeterminate
    assert state.compared_versions == ("2026-11",)


def test_immutable_file_segments_and_reconcile(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "journals", writer_id="run1")
    first = diagnostic_record()
    written = writer.write_batch((first,))
    assert written.state == "confirmed"
    assert written.guarantee == "immutable_read_back"
    assert writer.write_batch((first,)).already_present is True
    conflict = writer.write_batch((diagnostic_record(2),), segment_id=written.segment_id)
    assert conflict.state == "failed" and conflict.diagnostic_code == "journal.segment_conflict"
    assert reconcile_write(store, written).state == "confirmed"
    reader = FileJournalReader(store)
    assert list(reader.iter_segments((written.locator,), expected={written.locator: written.content_identity})) == [first]
    assert reader.read_report((written.locator,), expected_paths=frozenset({written.locator})).complete is False
    assert reader.read_report(("journals/missing.jsonl",)).issues[0].code == "journal.segment_missing"


def test_unknown_commit_can_be_reconciled(tmp_path):
    base = LocalFileStore(str(tmp_path))
    class CommitButNoAck:
        def makedirs(self, p):
            return base.makedirs(p)
        def create_if_absent(self, p, data):
            base.create_if_absent(p, data)
            raise ConnectionError("acknowledgement lost")
        def open_read(self, p):
            return base.open_read(p)
    writer = FileJournalWriter(CommitButNoAck(), "events", writer_id="attempt")
    receipt = writer.write_batch((diagnostic_record(),))
    assert receipt.state == "unknown"
    assert reconcile_write(base, receipt).state == "confirmed"
    with pytest.raises(JournalBarrierError):
        RequiredJournalGate(writer).require_confirmed(diagnostic_record(2))


def test_missing_capability_and_required_barrier(tmp_path):
    class NoAtomicStore:
        def makedirs(self, path):
            pass
    writer = FileJournalWriter(NoAtomicStore(), "events", writer_id="run")
    gate = RequiredJournalGate(writer)
    performed = []
    with pytest.raises(JournalBarrierError) as err:
        gate.execute_after_record(diagnostic_record(), lambda: performed.append("effect"))
    assert err.value.receipt.state == "failed"
    assert not performed
    working = RequiredJournalGate(FileJournalWriter(LocalFileStore(str(tmp_path)), "ok", writer_id="run"))
    value, receipt = working.execute_after_record(diagnostic_record(), lambda: "completed")
    assert value == "completed" and receipt.state == "confirmed"


def test_parallel_create_same_segment(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "parallel", writer_id="run")
    with ThreadPoolExecutor(max_workers=4) as executor:
        receipts = list(executor.map(lambda _: writer.write_batch((diagnostic_record(),)), range(8)))
    assert all(r.state == "confirmed" for r in receipts)
    assert sum(not r.already_present for r in receipts) == 1


def test_buffered_segment_and_recovery(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "buffers", writer_id="run", policy=PersistencePolicy(max_buffer_records=2))
    journal = BufferedFileJournal(writer)
    assert journal.append(diagnostic_record(1)) is None
    receipt = journal.append(diagnostic_record(2))
    assert receipt is not None and receipt.state == "confirmed"
    assert not journal.pending
    journal.append(diagnostic_record(3))
    written = journal.close()
    assert len(written) == 2
    assert list(FileJournalReader(store).iter_segments(r.locator for r in written)) == [
        diagnostic_record(1), diagnostic_record(2), diagnostic_record(3)]


def test_corrupt_segment_isolated_from_other_segments(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "recovery", writer_id="run")
    good = writer.write_batch((diagnostic_record(1),))
    bad = writer.write_batch((diagnostic_record(2),))
    (tmp_path / bad.locator).write_bytes(b'{bad-json\n')
    report = FileJournalReader(store).read_report((bad.locator, good.locator),
        expected={good.locator: good.content_identity, bad.locator: bad.content_identity})
    assert report.records == (diagnostic_record(1),)
    assert report.issues[0].code == "journal.segment_identity_mismatch"
    assert not report.complete


def test_projection_csv_explicit_columns():
    value = project_effect_state((diagnostic_record(),), "effect-1")
    assert value.needs_reconciliation
    rows = projection_rows((value,), ("effect_id", "needs_reconciliation"))
    assert b"effect_id,needs_reconciliation\n" in export_projection_csv(rows, columns=("effect_id", "needs_reconciliation"))
    with pytest.raises(ValueError):
        export_projection_csv(({"bad": "field"},), columns=("good",))


def test_capture_operation_comparison_semantics():
    from stratbox.observability import capture_operation_result
    spec = OperationDefinition("test.compare", 1, "compare-1", str, Comparison)
    result = run(spec, "irrelevant", lambda request, invocation: Comparison("new_release", "release.date_changed"),
                 context=ExecutionContext())
    collector = RecordMemorySink()
    captured = capture_operation_result(result, collector, occurred_at_utc=UTC,
                                        dataset_id="population", baseline_id="previous", candidate_id="current")
    assert captured.produced == captured.accepted == 2
    assert {r.kind for r in collector.records} == {"operation.result", "dataset.comparison_completed"}
    assert project_dataset_state(collector.records, "population").latest_comparison == "new_release"


def test_file_sink_is_optional_and_flush_is_explicit(tmp_path):
    from stratbox.observability import FileEventSink
    writer = FileJournalWriter(LocalFileStore(str(tmp_path)), "events", writer_id="session",
                               policy=PersistencePolicy(max_buffer_records=2))
    sink = FileEventSink(BufferedFileJournal(writer))
    result = execute(sink)
    assert result.outcome == "succeeded"
    final = sink.close()
    assert len(final) == 2
    assert all(r.state == "confirmed" for r in final)
    history = FileJournalReader(LocalFileStore(str(tmp_path))).read_report(tuple(r.locator for r in final))
    assert len(history.records) == 3
    assert [r.kind for r in history.records] == ["operation.started", "operation.stage", "operation.finished"]


def test_source_check_and_artifact_facts_keep_confirmation_separate():
    from stratbox.observability import fact_for_source_check, fact_for_artifact, project_artifact_state
    checked = record_from_fact(fact_for_source_check(source_id="statistics", checked_at_utc=UTC,
                                                     status="succeeded", version_id="2026-11"))
    assert checked.kind == "source.checked"
    identity = ByteIdentity.of(b"document")
    produced = record_from_fact(fact_for_artifact(artifact_id="report", identity=identity,
                                                  occurred_at_utc=UTC))
    state = project_artifact_state((produced,), "report")
    assert state.produced and not state.stored_confirmed
    with pytest.raises(ValueError):
        fact_for_artifact(artifact_id="report", identity=identity, occurred_at_utc=UTC,
                          stored=True, receipt_status="unknown")
    confirmed = record_from_fact(fact_for_artifact(artifact_id="report", identity=identity,
                                                   occurred_at_utc=UTC, stored=True,
                                                   receipt_status="confirmed"))
    assert project_artifact_state((produced, confirmed), "report").stored_confirmed


def test_payload_is_snapshot_not_mutable_caller_state():
    value = {"entries": [{"field": "original"}]}
    record = diagnostic_record(payload=value)
    value["entries"][0]["field"] = "changed"
    assert record.payload["entries"][0]["field"] == "original"
    with pytest.raises(TypeError):
        record.payload["entries"][0]["field"] = "other"
    decoded, = decode_records(encode_records((record,)))
    assert decoded == record


def test_read_report_complete_requires_evidence_manifest(tmp_path):
    store = LocalFileStore(str(tmp_path))
    receipt = FileJournalWriter(store, "complete", writer_id="run").write_batch((diagnostic_record(),))
    reader = FileJournalReader(store)
    assert not reader.read_report((receipt.locator,), expected_paths=frozenset((receipt.locator,))).complete
    assert not reader.read_report((receipt.locator,), expected_paths=frozenset((receipt.locator,)),
                                  capture_complete=True).complete
    assert reader.read_report((receipt.locator,), expected_paths=frozenset((receipt.locator,)),
                              expected={receipt.locator: receipt.content_identity},
                              capture_complete=True).complete


def test_partial_corrupt_segment_never_yields_confirmed_prefix(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "corruption", writer_id="run")
    segment = writer.write_batch((diagnostic_record(1), diagnostic_record(2)))
    path = tmp_path / segment.locator
    path.write_bytes(encode_records((diagnostic_record(1),)) + b"{invalid\n")
    report = FileJournalReader(store).read_report((segment.locator,))
    assert report.records == ()
    assert report.issues[0].code == "journal.json_invalid"
    assert report.issues[0].line == 2


def test_parent_from_another_invocation_is_known():
    parent = diagnostic_record(1)
    child = JournalRecord("dependent", "result_summary", "operation.result", UTC, {},
                          invocation_id="invocation", operation_id="test",
                          cause_record_ids=(parent.record_id,))
    history = build_operation_history((parent, child), "invocation")
    assert history.missing_causes == ()


def test_source_check_state_exposes_payload_status():
    from stratbox.observability import fact_for_source_check, project_source_state
    rec = record_from_fact(fact_for_source_check(source_id="stats", checked_at_utc=UTC,
                                                 status="succeeded"))
    state = project_source_state((rec,), "stats")
    assert state.last_check_outcome == "succeeded"


def test_history_policy_filtered_progress_is_not_a_false_loss():
    sink = RecordMemorySink(CapturePolicy(progress=False))
    result = execute(sink)
    history = build_operation_history(sink.records, result.invocation_id,
                                      capture_complete=True, progress_filtered=True)
    assert history.coverage == "complete"
    assert history.missing_sequences
    assert "journal.sequence_gap" not in history.problems


def test_causal_aliases_resolve_execution_event_ids():
    from stratbox.observability import record_from_execution_event
    from stratbox.execution import ExecutionEvent
    parent_event = ExecutionEvent(3, "operation.started", "parent", "op", 1, "method", 1, UTC, Correlation())
    child_event = ExecutionEvent(3, "operation.started", "child", "op", 1, "method", 1, UTC,
                                 Correlation(cause_event_id=parent_event.event_id))
    parent = record_from_execution_event(parent_event)
    child = record_from_execution_event(child_event)
    inspection = inspect_causes((parent, child), child.record_id)
    assert {x.record_id for x in inspection.roots} == {parent.record_id, child.record_id}
    assert inspection.missing_parent_ids == ()
    assert build_operation_history((parent, child), "child").missing_causes == ()


def test_duplicate_segments_are_deduplicated(tmp_path):
    store = LocalFileStore(str(tmp_path))
    w = FileJournalWriter(store, "dup", writer_id="run")
    first = w.write_batch((diagnostic_record(1),))
    report = FileJournalReader(store).read_report((first.locator, first.locator))
    assert report.records == (diagnostic_record(1),)
    assert not report.issues


def test_memory_sink_is_bounded_by_bytes_not_only_record_count():
    a = diagnostic_record(payload={"description": "x" * 4000})
    policy = CapturePolicy(max_records=10, max_bytes=4500)
    sink = RecordMemorySink(policy)
    assert sink.capture(a)
    assert not sink.capture(diagnostic_record(2, payload={"description": "z" * 4000}))
    assert sink.dropped == 1
    assert 4000 < sink.bytes_used < 4500
