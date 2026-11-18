"""OBS-01..OBS-14 and coverage/manifest counterexamples; all offline."""
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dataclasses import dataclass
import csv
import io
import json
import pytest

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.evidence import PublicationReceipt, StoredBytesReceipt
from stratbox.core.execution import (Correlation, Diagnostic, EffectReceipt,
                                ObservabilitySummary, OperationDefinition, OperationResult,
                                ExecutionEvent, ExecutionContext, run)
from stratbox.core.observability import (
    CapturePolicy, PersistencePolicy, PresentationPolicy, RecordMemorySink, FileEventSink,
    JournalRecord, JournalNamespace, DomainFact, ObjectRef, PayloadLimits, OriginClaim,
    OriginAttestation, JournalBarrierError, RecordFilter, select_records,
    summarize_operations, build_operation_history, SequenceRange, find_gaps,
    merge_ranges, subtract_ranges, count_ranges, intersect_ranges, CaptureCoverage,
    assess_coverage, record_from_result, record_from_fact, record_from_execution_event,
    fact_from_stored_bytes, fact_from_publication, fact_from_comparison,
    project_effect_state, project_source_state, project_dataset_state,
    project_artifact_state, project_operation_state, operation_state_from_result,
    artifact_state_from_storage, dataset_state_from_comparison, effect_state_from_result,
    fact_for_source_check, fact_for_artifact, FileJournalWriter, FileJournalReader,
    BufferedFileJournal, RequiredJournalGate, reconcile_write, encode_records,
    decode_records, JournalDecodeError, export_projection_csv, inspect_causes,
    build_manifest, SegmentDescriptor, ObserverHealthSnapshot, CaptureDisposition,
    capture_operation_result, group_records, make_fact_id,
)

TIME = datetime(2026, 11, 15, tzinfo=timezone.utc)


def event(n, kind, invocation="run", *, code=None):
    return ExecutionEvent(3, kind, invocation, "test.observed", 1, "method-1", n,
                          TIME, Correlation(), diagnostic_code=code, outcome="succeeded" if kind == "operation.finished" else None)


def record(n, kind, invocation="run"):
    return record_from_execution_event(event(n, kind, invocation))


def diagnostic(name="d1", payload=None):
    return JournalRecord(name, "diagnostic", "validation.issue_detected", TIME,
                         payload if payload is not None else {"diagnostic_code": "http.timeout"})


def run_test(sink=None):
    definition = OperationDefinition("test.observed", 1, "method-1", str, str)
    def work(s, invocation):
        invocation.stage("parse")
        invocation.progress(1, 1)
        return s.upper()
    return run(definition, "hello", work, context=ExecutionContext(sink=sink))


def test_mapping_proxy_diagnostics_and_effects():
    spec = OperationDefinition("test.observed", 1, "method-1", str, str, possible_effects=frozenset({"storage.write"}))
    result = OperationResult(spec, "attempt1", "succeeded", "answer",
                             (Diagnostic("http.timeout"),), (),
                             (EffectReceipt("storage.write", "confirmed", effect_id="E1"),),
                             ObservabilitySummary(0, 0))
    item = record_from_result(result, occurred_at_utc=TIME)
    assert list(select_records((item,), RecordFilter(diagnostic_code="http.timeout"))) == [item]
    history = build_operation_history((record(1, "operation.started", "attempt1"),
                                       record(2, "operation.finished", "attempt1"), item), "attempt1")
    assert summarize_operations((history,)).diagnostic_codes == {"http.timeout": 1}
    state = project_effect_state((item,), "E1")
    assert state.states == ("confirmed",) and not state.needs_reconciliation
    decoded, = decode_records(encode_records((item,)))
    assert project_effect_state((decoded,), "E1") == state


@pytest.mark.parametrize("storage_status,effect_state", [
    ("stored", "confirmed"), ("already_present", "confirmed"),
    ("failed", "failed"), ("unknown", "unknown"),
])
def test_storage_status_mapping(storage_status, effect_state):
    receipt = StoredBytesReceipt("/private/path", ByteIdentity.of(b"hello"),
                                 storage_status, "atomic_create", "local", effect_id="effect_1")
    fact = fact_from_stored_bytes(receipt, subject_id="source_1", observed_at_utc=TIME)
    assert fact.payload["effect_state"] == effect_state
    assert fact.references[0].object_id == "effect_1"
    rec = record_from_fact(fact)
    assert project_effect_state((rec,), "effect_1").states == (effect_state,)
    assert project_effect_state(decode_records(encode_records((rec,))), "effect_1").states == (effect_state,)
    assert "/private/path" not in encode_records((rec,)).decode("utf-8")


def test_source_history_is_not_a_conflict():
    a = PublicationReceipt("source_1", "dataset", "oct", "a", ByteIdentity.of(b"a"), "confirmed")
    b = PublicationReceipt("source_1", "dataset", "nov", "b", ByteIdentity.of(b"b"), "confirmed")
    records = (record_from_fact(fact_from_publication(a, occurred_at_utc=TIME)),
               record_from_fact(fact_from_publication(b, occurred_at_utc=TIME)))
    state = project_source_state(records, "source_1")
    assert not state.conflict and state.current_release_id is None
    assert state.confirmed_releases == ("nov", "oct")
    assert project_source_state(records, "source_1", resolver=lambda releases: "nov").current_release_id == "nov"


def test_source_same_release_competing_byte_id_conflict():
    left = PublicationReceipt("source_1", "dataset", "oct", "a", ByteIdentity.of(b"a"), "confirmed")
    right = PublicationReceipt("source_1", "dataset", "oct", "b", ByteIdentity.of(b"b"), "confirmed")
    records = (record_from_fact(fact_from_publication(left, occurred_at_utc=TIME)),
               record_from_fact(fact_from_publication(right, occurred_at_utc=TIME)))
    assert not project_source_state(records, "source_1").conflict
    assert project_source_state(records, "source_1").indeterminate


def test_dataset_sequential_pairs_not_conflict():
    facts = [fact_from_comparison(Comparison(state, "reason"), dataset_id="dataset_1",
                                  baseline_id=a, candidate_id=b, occurred_at_utc=TIME)
             for a,b,state in [("a", "b", "unchanged"), ("b", "c", "new_release")]]
    records = tuple(map(record_from_fact, facts))
    s = project_dataset_state(records, "dataset_1")
    assert not s.conflict and s.latest_comparison is None and s.indeterminate
    assert s.compared_versions == ("b", "c")


def test_dataset_conflict_for_same_comparison():
    fact_a = fact_from_comparison(Comparison("unchanged", "same"), dataset_id="d", baseline_id="a",
                                  candidate_id="b", occurred_at_utc=TIME)
    fact_b = fact_from_comparison(Comparison("revised", "different"), dataset_id="d", baseline_id="a",
                                  candidate_id="b", occurred_at_utc=TIME)
    s = project_dataset_state((record_from_fact(fact_a), record_from_fact(fact_b)), "d")
    assert s.conflict and s.indeterminate


def test_result_status_distinct_from_event_coverage():
    result = run_test()
    assert operation_state_from_result(result).result_known
    assert operation_state_from_result(result).event_coverage == "not_collected"


def test_record_from_result_observation_identity_and_canonical_finish():
    result = run_test()
    first = record_from_result(result, occurred_at_utc=TIME, observation_id="observe_1")
    second = record_from_result(result, occurred_at_utc=TIME, observation_id="observe_2")
    again = record_from_result(result, occurred_at_utc=TIME, observation_id="observe_1")
    assert first.record_id != second.record_id and first == again
    assert first.payload["time_basis"] == "observation"
    finish = event(4, "operation.finished", result.invocation_id)
    final_a = record_from_result(result, finished_event=finish)
    final_b = record_from_result(result, finished_event=finish)
    assert final_a == final_b
    assert final_a.payload["time_basis"] == "producer_finished_event"


def test_coverage_progress_evidence_and_lost_stage():
    one = record(1, "operation.started")
    progress = record(3, "operation.progress")
    done = record(4, "operation.finished")
    # The stage at 2 is missing, even though progress is disabled elsewhere.
    cover = CaptureCoverage("run", "lifecycle_without_progress", 4, (SequenceRange(1, 1),
         SequenceRange(3, 4)), (SequenceRange(3,3),), (), 0, 0, True, None, "collector_observed", True)
    h = build_operation_history((one, progress, done), "run", coverage=cover)
    assert h.coverage == "incomplete" and h.missing_sequence_count == 1
    good = CaptureCoverage("run", "lifecycle_without_progress", 4,
        (SequenceRange(1,4),), (SequenceRange(2,2),), (), 0, 0, True, None, "collector_observed", True)
    h2 = build_operation_history((one, record(3, "operation.stage"), done), "run", coverage=good)
    assert h2.coverage == "complete"
    assert h2.missing_sequence_ranges == (SequenceRange(2,2),)


def test_unknown_gap_near_max_safe_memory():
    last = 2**53 - 2
    h = build_operation_history((record(1,"operation.started"), record(last,"operation.finished")), "run")
    assert h.missing_sequence_ranges == (SequenceRange(2,last-1),)
    assert h.missing_sequence_count == last-2
    assert h.sample_missing_sequences(3) == (2,3,4)
    assert h.coverage != "complete"


def test_range_algebra():
    assert merge_ranges((SequenceRange(2,4), SequenceRange(5,7), SequenceRange(3,3))) == (SequenceRange(2,7),)
    assert subtract_ranges((SequenceRange(1,10),), (SequenceRange(2,3), SequenceRange(8,9))) == (
        SequenceRange(1,1),SequenceRange(4,7),SequenceRange(10,10))
    assert intersect_ranges((SequenceRange(1,6),), (SequenceRange(3,8),)) == (SequenceRange(3,6),)
    assert count_ranges((SequenceRange(1,3),SequenceRange(3,5))) == 5
    assert find_gaps((1,5),expected_last=7) == (SequenceRange(2,4),SequenceRange(6,7))


def test_memory_collector_proves_excluded_progress():
    memory = RecordMemorySink(CapturePolicy(progress=False))
    result = run_test(memory)
    assert result.outcome == "succeeded"
    cover = memory.coverage_for(result.invocation_id, producer=result.observability)
    history = build_operation_history(memory.records, result.invocation_id, coverage=cover)
    assert cover.policy_excluded_ranges == (SequenceRange(3,3),)
    assert history.coverage == "complete"
    health = memory.health_snapshot(producer=result.observability)
    assert health.policy_filtered == 1 and health.collector_dropped == 0


def test_collector_capacity_loss_not_filtered():
    memory = RecordMemorySink(CapturePolicy(max_records=1, progress=True))
    result = run_test(memory)
    evidence = memory.coverage_for(result.invocation_id, producer=result.observability)
    history = build_operation_history(memory.records, result.invocation_id, coverage=evidence)
    assert history.coverage == "incomplete"
    assert memory.dropped > 0 and memory.policy_filtered == 0


def test_deep_nested_payload_and_large_number_budget():
    content = {"small": [dict(x=i) for i in range(1024)]}
    rec = diagnostic(payload=content)
    assert len(rec.payload["small"]) == 1024
    with pytest.raises(ValueError):
        diagnostic(payload={"wide": [dict(x=i) for i in range(10_000)]})
    with pytest.raises((ValueError, TypeError)):
        diagnostic(payload={"decimal": Decimal("1." + "1" * 1200)})
    value = {"a": 1}
    rec = diagnostic(payload={"nested": value})
    value["a"] = 2
    assert rec.payload["nested"]["a"] == 1
    with pytest.raises(TypeError):
        rec.payload["nested"]["a"] = 3
    with pytest.raises(ValueError):
        diagnostic(payload={"$stratbox_decimal": "42"})


def test_jsonl_tags_decimal_big_int_and_bad_schema():
    v = diagnostic(payload={"value": Decimal("1.000000000000001"), "big":2**64})
    for fmt in ("json", "jsonl"):
        decoded, = decode_records(encode_records((v,), format=fmt), format=fmt)
        assert decoded == v and type(decoded.payload["big"]) is int
    d = json.loads(encode_records((v,), format="json"))
    d[0]["schema_version"] = 44
    with pytest.raises(JournalDecodeError) as exc:
        decode_records(json.dumps(d).encode(), format="json")
    assert exc.value.code == "journal.unsupported_schema"
    with pytest.raises(JournalDecodeError):
        decode_records(b'\xff\xfe')


@pytest.mark.parametrize("attack", ["=SUM(1,1)", "+SUM(A1,A2)", "-cmd", "@user", "\t=2+3", "\r=2+3", "  =1+1"])
def test_csv_spreadsheet_formula_protection(attack):
    data = export_projection_csv(({"payload":attack,"value":-12},),columns=("payload","value"))
    reader = csv.DictReader(io.StringIO(data.decode()))
    row = next(reader)
    assert row["payload"].startswith("'")
    assert row["value"] == "-12"
    plain = export_projection_csv(({"payload":attack},), columns=("payload",), spreadsheet_safe=False)
    assert next(csv.DictReader(io.StringIO(plain.decode())))["payload"] == attack
    with pytest.raises(ValueError):
        export_projection_csv(({"SECRET":"value"},), columns=("payload",))


def test_reconcile_read_exactly_once(tmp_path):
    base = LocalFileStore(tmp_path)
    writer = FileJournalWriter(base, "logs", writer_id="one")
    receipt = writer.write_batch((diagnostic(),))
    assert receipt.state == "confirmed"
    class MutatingReads:
        reads=0
        def open_read(self,path):
            self.reads+=1
            if self.reads > 1:
                return io.BytesIO(b"bad")
            return base.open_read(path)
    store=MutatingReads()
    result=reconcile_write(store,receipt,namespace=writer.namespace)
    assert result.state == "confirmed" and store.reads == 1


def test_namespace_reconcile_no_path_escape(tmp_path):
    base=LocalFileStore(tmp_path)
    writer=FileJournalWriter(base,"logs",writer_id="test")
    receipt=writer.write_batch((diagnostic(),))
    with pytest.raises(ValueError):
        reconcile_write(base,replace(receipt,locator="elsewhere/private.jsonl"),namespace=writer.namespace)
    with pytest.raises(ValueError):
        FileJournalWriter(base,"../outside",writer_id="test")
    with pytest.raises(ValueError):
        FileJournalWriter(base,"/absolute",writer_id="test")


def test_buffer_unknown_then_reconcile(tmp_path):
    base=LocalFileStore(tmp_path)
    class LostAck:
        def makedirs(self,path):return base.makedirs(path)
        def open_read(self,path):return base.open_read(path)
        def create_if_absent(self,path,data):
            base.create_if_absent(path,data)
            raise OSError("lost acknowledgement")
    writer=FileJournalWriter(LostAck(),"pending",writer_id="run",policy=PersistencePolicy(max_buffer_records=1))
    journal=BufferedFileJournal(writer)
    receipt=journal.append(diagnostic())
    assert receipt.state == "unknown" and len(journal.pending)==1
    assert journal.close_status == "pending_unconfirmed"
    first=journal.flush()
    assert first == receipt # no unsafe retry or new segment id
    journal.writer=FileJournalWriter(base,"pending",writer_id="run",policy=PersistencePolicy(max_buffer_records=1))
    assert journal.reconcile_pending().state == "confirmed"
    journal.close()
    assert journal.close_status == "closed_confirmed"


def test_file_manifest_seal_full_roundtrip(tmp_path):
    store=LocalFileStore(tmp_path)
    writer=FileJournalWriter(store,"journals",writer_id="writer1")
    sink=RecordMemorySink(CapturePolicy(progress=False), origin=OriginClaim("test", "collector", "generation1"))
    result=run_test(sink)
    snapshot=sink.records
    cov=sink.coverage_for(result.invocation_id,producer=result.observability)
    h=build_operation_history(snapshot,result.invocation_id,coverage=cov)
    assert h.coverage=="complete"
    assess=assess_coverage((rec.sequence for rec in snapshot if rec.record_type=="execution"), cov,
                            start_seen=True,terminal_seen=True)
    receipt=writer.write_batch(snapshot)
    assert receipt.state=="confirmed"
    manifest=build_manifest(writer_id="writer1", generation_id="generation1",scope_id=cov.scope_id,
                            segments=(SegmentDescriptor.from_receipt(receipt),),records=snapshot,sealed_at_utc=TIME,
                            capture_evidence=(cov,))
    assert manifest.seal_state=="sealed"
    manifest_receipt=writer.write_manifest(manifest)
    reader=FileJournalReader(store,namespace=writer.namespace)
    recovered=reader.load_manifest(manifest_receipt)
    assert recovered==manifest
    report=reader.read_report(manifest_receipt=manifest_receipt)
    assert report.complete and report.records==snapshot
    assert project_operation_state(report.records,result.invocation_id,coverage=cov).event_coverage=="complete"
    (tmp_path/receipt.locator).write_bytes(b'{bad\n')
    bad=reader.read_report(manifest_receipt=manifest_receipt)
    assert not bad.complete and not bad.records and bad.issues


def test_optional_file_sink_composition(tmp_path):
    store=LocalFileStore(tmp_path)
    writer=FileJournalWriter(store,"fsink",writer_id="writer1",policy=PersistencePolicy(max_buffer_records=2))
    sink=FileEventSink(BufferedFileJournal(writer))
    result=run_test(sink)
    assert result.outcome=="succeeded"
    assert sink.close()
    assert sink.health_snapshot().flush_confirmed>=1
    assert not sink.journal.pending
    reader=FileJournalReader(store,namespace=writer.namespace)
    report=reader.read_report([receipt.locator for receipt in sink.journal.receipts])
    assert report.storage_coverage=="indeterminate" and not report.complete
    assert len(report.records)==3


def test_gate_precedes_effect_and_does_not_confirm_callback(tmp_path):
    store=LocalFileStore(tmp_path)
    good=RequiredJournalGate(FileJournalWriter(store,"gate",writer_id="test"))
    called=[]
    answer, receipt=good.execute_after_record(diagnostic(),lambda:called.append(1))
    assert called==[1] and receipt.state=="confirmed"
    class Broken:
        format = "jsonl"

        def write_batch(self,*a,**kw):return replace(receipt,state="unknown")
    with pytest.raises(JournalBarrierError):
        RequiredJournalGate(Broken()).execute_after_record(diagnostic(),lambda:called.append(2))
    assert called==[1]
    with pytest.raises(RuntimeError):
        good.execute_after_record(diagnostic("next"),lambda: (_ for _ in ()).throw(RuntimeError("business failed")))


def test_causal_iterative_long_chain_and_truncation():
    records=[]
    for n in range(2000):
        records.append(JournalRecord(f"node{n}","diagnostic","test.dependency",TIME,{},
                                     cause_record_ids=((f"node{n-1}",) if n else ())))
    result=inspect_causes(records,"node1999",max_nodes=3000,max_depth=2500)
    assert len(result.roots)==2000 and not result.missing_parent_ids
    partial=inspect_causes(records,"node1999",max_nodes=100)
    assert partial.truncated and len(partial.roots)<=100


def test_origin_claim_cannot_self_attest():
    with pytest.raises(ValueError):
        OriginClaim("worker","collector","gen",authority_level="host_verified")
    claim=OriginClaim("worker","collector","gen")
    assert claim.authority_level=="claimed"


def test_manifest_missing_segment_or_manifest_corrupt(tmp_path):
    store=LocalFileStore(tmp_path)
    writer=FileJournalWriter(store,"m",writer_id="one")
    receipt=writer.write_batch((record(1, "operation.started", "inv"), record(2, "operation.finished", "inv")))
    evidence_object=CaptureCoverage("inv","scope",2,(SequenceRange(1,2),),
                       terminal_seen=True,evidence_quality="collector_observed",start_seen=True,generation_id="gen")
    evidence=assess_coverage((1,2),evidence_object,start_seen=True,terminal_seen=True)
    manifest=build_manifest(writer_id="one",generation_id="gen",scope_id="scope",
                segments=(SegmentDescriptor.from_receipt(receipt),),records=(record(1, "operation.started", "inv"), record(2, "operation.finished", "inv")),sealed_at_utc=TIME,
                capture_evidence=(evidence_object,))
    mr=writer.write_manifest(manifest)
    reader=FileJournalReader(store,namespace=writer.namespace)
    assert reader.read_report(manifest_receipt=mr).complete
    (tmp_path/receipt.locator).unlink()
    assert not reader.read_report(manifest_receipt=mr).complete
    (tmp_path/mr.locator).write_bytes(b'{}')
    failed=reader.read_report(manifest_receipt=mr)
    assert failed.issues[0].code=="journal.manifest_identity_mismatch"


def test_grouping_budget_and_codec_limit():
    with pytest.raises(ValueError):
        group_records((diagnostic(f"d{i}") for i in range(100)),lambda r:r.record_id,max_records=10)
    with pytest.raises(JournalDecodeError):
        decode_records(encode_records((diagnostic(),)),max_bytes=2)


def test_composite_optional_observers_isolate_failures():
    from stratbox.core.observability import CompositeEventSink
    class Broken:
        def emit(self, event):
            raise RuntimeError("failure must not escape to sibling")
    collector = RecordMemorySink()
    composite = CompositeEventSink(Broken(), collector)
    result = run_test(composite)
    assert result.outcome == "succeeded"
    assert composite.dropped >= 2
    assert len(collector.records) == 3
    assert composite.recipient_failures[0] == composite.dropped
    assert composite.recipient_failures[1] == 0


def test_domain_fact_id_separate_from_observation():
    subject = ObjectRef("dataset", "test")
    stable = make_fact_id("dataset.changed", subject, {"version": "nov"})
    a = DomainFact("dataset.changed", subject, stable, TIME, {"value": 2}, observation_id="a")
    b = DomainFact("dataset.changed", subject, stable, TIME, {"value": 2}, observation_id="b")
    assert a.fact_id == b.fact_id
    assert record_from_fact(a).record_id != record_from_fact(b).record_id


def test_invalid_time_and_corrupt_suffix():
    with pytest.raises(ValueError):
        JournalRecord("bad", "diagnostic", "invalid.time", datetime(2026,11,15), {})
    clean = encode_records((diagnostic(),))
    with pytest.raises(JournalDecodeError) as error:
        decode_records(clean + b"{broken\n")
    assert error.value.line == 2


def test_storage_segment_collision_and_identical_idempotence(tmp_path):
    store = LocalFileStore(tmp_path)
    writer = FileJournalWriter(store, "immut", writer_id="w")
    first = writer.write_batch((diagnostic("one"),), segment_id="chosen")
    second = writer.write_batch((diagnostic("one"),), segment_id="chosen")
    different = writer.write_batch((diagnostic("other"),), segment_id="chosen")
    assert first.state == second.state == "confirmed"
    assert second.already_present
    assert different.state == "failed" and different.diagnostic_code == "journal.segment_conflict"


def test_no_fabricated_source_revision_and_check_state():
    fact = fact_from_comparison(Comparison("indeterminate", "baseline.unavailable"),
                                dataset_id="x", baseline_id=None,
                                candidate_id="nov", occurred_at_utc=TIME)
    state = project_dataset_state((record_from_fact(fact),), "x")
    assert state.indeterminate and state.latest_comparison == "indeterminate"
    checks = (record_from_fact(fact_for_source_check(source_id="x", checked_at_utc=TIME,
                                                     status="succeeded",version_id="nov")),)
    assert project_source_state(checks, "x").last_check_outcome == "succeeded"


def test_artifact_produced_not_stored_until_receipt():
    identity = ByteIdentity.of(b"report")
    produced = record_from_fact(fact_for_artifact(artifact_id="report", identity=identity,
                                                  occurred_at_utc=TIME))
    state = project_artifact_state((produced,), "report")
    assert state.produced and not state.stored_confirmed
    with pytest.raises(ValueError):
        fact_for_artifact(artifact_id="report", identity=identity, occurred_at_utc=TIME,
                          stored=True, receipt_status="unknown")
    saved = record_from_fact(fact_for_artifact(artifact_id="report", identity=identity,
                                                occurred_at_utc=TIME, stored=True, receipt_status="stored"))
    assert project_artifact_state((produced, saved), "report").stored_confirmed


def test_corrupt_segment_never_exposes_good_prefix(tmp_path):
    writer = FileJournalWriter(LocalFileStore(tmp_path), "bad", writer_id="w")
    receipt = writer.write_batch((diagnostic("one"),diagnostic("two")))
    path = tmp_path / receipt.locator
    path.write_bytes(encode_records((diagnostic("one"),)) + b"{broken\n")
    report = FileJournalReader(writer.store, namespace=writer.namespace).read_report((receipt.locator,))
    assert report.records == ()
    assert report.issues[0].code == "journal.json_invalid"


def test_causal_alias_and_foreign_invocation_parent():
    parent = record(1, "operation.started", "inv_parent")
    child_event = ExecutionEvent(3, "operation.started", "inv_child", "test.observed", 1,
                                 "method-1", 1, TIME, Correlation(cause_event_id="inv_parent.1"))
    child = record_from_execution_event(child_event)
    detail = inspect_causes((parent,child),child.record_id)
    assert {x.record_id for x in detail.roots} == {parent.record_id,child.record_id}
    assert not detail.missing_parent_ids
    assert not build_operation_history((parent,child),"inv_child").missing_causes


def test_duplicate_segments_are_deduplicated(tmp_path):
    writer=FileJournalWriter(LocalFileStore(tmp_path),"repeat",writer_id="w")
    receipt=writer.write_batch((diagnostic(),))
    report=FileJournalReader(writer.store,namespace=writer.namespace).read_report((receipt.locator,receipt.locator))
    assert not report.issues and report.records==(diagnostic(),)


def test_capture_comparison_never_reexecutes_business_code():
    spec=OperationDefinition("test.comparison",1,"method-1",str,Comparison)
    invocations=[]
    def business(request, invocation):
        invocations.append(request)
        return Comparison("new_release","release.date_changed")
    result=run(spec,"single",business)
    collector=RecordMemorySink()
    report=capture_operation_result(result,collector,occurred_at_utc=TIME,
                                    dataset_id="population",baseline_id="prev",candidate_id="now")
    assert report.produced==report.accepted==2
    assert invocations==["single"]
    assert project_dataset_state(collector.records,"population").latest_comparison=="new_release"


def test_manifest_complete_needs_collector_evidence(tmp_path):
    writer=FileJournalWriter(LocalFileStore(tmp_path),"unverified",writer_id="w")
    receipt=writer.write_batch((record(1,"operation.started"),record(2,"operation.finished")))
    qualified=assess_coverage((1,2),CaptureCoverage("run","scope",2,(SequenceRange(1,2),),
             terminal_seen=True,evidence_quality="collector_observed",start_seen=True),
             start_seen=True,terminal_seen=True)
    manifest=build_manifest(writer_id="w",generation_id="g",scope_id="scope",
        segments=(SegmentDescriptor.from_receipt(receipt),),records=(record(1,"operation.started"),record(2,"operation.finished")),sealed_at_utc=TIME)
    assert manifest.seal_state=="incomplete"
    mr=writer.write_manifest(manifest)
    assert not FileJournalReader(writer.store,namespace=writer.namespace).read_report(manifest_receipt=mr).complete


def test_artifact_unknown_versions_do_not_fake_conflict():
    a = record_from_fact(fact_for_artifact(artifact_id="forecast", identity=ByteIdentity.of(b"a"), occurred_at_utc=TIME))
    b = record_from_fact(fact_for_artifact(artifact_id="forecast", identity=ByteIdentity.of(b"b"), occurred_at_utc=TIME))
    result = project_artifact_state((a,b), "forecast")
    assert result.indeterminate and not result.conflicting_identity and result.identity_sha256 is None
    known_version_a = record_from_fact(fact_for_artifact(artifact_id="forecast", identity=ByteIdentity.of(b"a"),
                                                    occurred_at_utc=TIME, version_id="v1"))
    known_version_b = record_from_fact(fact_for_artifact(artifact_id="forecast", identity=ByteIdentity.of(b"b"),
                                                    occurred_at_utc=TIME, version_id="v1"))
    assert project_artifact_state((known_version_a,known_version_b), "forecast",version_id="v1").conflicting_identity


def test_finished_event_result_mismatch_rejected():
    result = run_test()
    mismatched = event(3,"operation.finished",result.invocation_id)
    mismatched = replace(mismatched, outcome="failed")
    with pytest.raises(ValueError):
        record_from_result(result,finished_event=mismatched)


def test_file_event_sink_policy_filter_counts_as_seen_but_not_lost(tmp_path):
    from stratbox.core.observability import FileEventSink
    from stratbox.core.execution import ExecutionContext, OperationDefinition, run
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "sink", writer_id="collector")
    collector = FileEventSink(BufferedFileJournal(writer), CapturePolicy(progress=False))
    result = run(OperationDefinition("sample.file_sink", 1, "v1", str, str), "ok",
                 lambda value, invocation: (invocation.stage("work"), invocation.progress(1, 1), value)[-1],
                 context=ExecutionContext(sink=collector))
    assert result.outcome == "succeeded"
    assert collector.dropped == 0
    assert collector.health_snapshot(producer=result.observability).policy_filtered == 1
    coverage = collector.coverage_for(result.invocation_id, producer=result.observability)
    assert coverage.policy_excluded_ranges == (SequenceRange(3, 3),)
    receipts = collector.close()
    assert all(x.state == "confirmed" for x in receipts)
