from dataclasses import replace
from datetime import datetime, timezone
from threading import Event
from time import monotonic

import pytest

from stratbox.core.execution import Correlation, ExecutionContext, OperationDefinition, run
from stratbox.core.observability import (
    FieldSchemaRegistry, JournalDecodeError, JournalReadLimits, OrchestrationEvent,
    OrchestrationJournal, RecordFilter, decode_record, encode_record,
    record_from_orchestration_event, select_records,
)

TIME = datetime(2026, 11, 24, tzinfo=timezone.utc)


def correlation(run_id="run", **kwargs):
    return Correlation(session_id="session", run_id=run_id, plan_id="plan", **kwargs)


def finish(journal, run_id="run", outcome="succeeded"):
    return journal.emit("run.finished", correlation(run_id), outcome=outcome,
                        counters={"succeeded": 1}, completed=1, total=1)


def test_orchestration_roundtrip_and_invocation_correlations_share_task_identity():
    corr = correlation(workflow_scope_id="scope", task_id="task", attempt_id="attempt", item_key="item")
    event = OrchestrationEvent("task.started", "session", 1, TIME, corr)
    record = record_from_orchestration_event(event)
    assert decode_record(encode_record(record)) == record
    FieldSchemaRegistry().validate(record)
    assert record.operation_id is record.invocation_id is None
    assert corr.step_id == corr.task_id == "task"
    with pytest.raises(ValueError, match="task_identity_conflict"):
        replace(corr, step_id="another")
    journal = OrchestrationJournal("session")
    result = run(OperationDefinition("test.add", "add", int, int), 1,
                 lambda value, invocation: value + 1,
                 context=ExecutionContext(correlation=corr, sink=journal))
    assert result.outcome == "succeeded"
    operation_finished = journal.records[-1]
    assert operation_finished.correlation == corr
    assert decode_record(encode_record(operation_finished)).correlation == corr
    assert list(select_records(journal.records, RecordFilter(task_id="task"))) == list(journal.records)


def test_telemetry_eviction_never_loses_reserved_terminal_evidence():
    journal = OrchestrationJournal("session", max_records=2, max_pending_runs=1)
    journal.reserve_run("run")
    for _ in range(8):
        journal.emit("task.ready", correlation(task_id="task"))
    terminal = finish(journal)
    for _ in range(8):
        journal.emit("task.waiting", correlation(task_id="task"), reason="resource")
    assert terminal not in journal.records
    head = journal.source.head(journal.stream)
    page = journal.source.read_page(head.cursor(0), head=head, limits=JournalReadLimits())
    page.verify(head.cursor(0), head, JournalReadLimits())
    assert page.entries[0].record == terminal
    assert page.capture_coverage == "complete"
    assert journal.health_snapshot().coverage == "incomplete"
    with pytest.raises(ValueError, match="retention_capacity"):
        journal.reserve_run("next")
    journal.acknowledge(1)
    journal.reserve_run("next")
    with pytest.raises(JournalDecodeError, match="cursor_expired"):
        journal.source.read_page(head.cursor(0), head=head, limits=JournalReadLimits())


def test_live_source_pinned_head_and_partial_page_are_consistent():
    journal = OrchestrationJournal("session")
    journal.reserve_run("a")
    first = finish(journal, "a", "partial")
    old_head = journal.source.head(journal.stream)
    journal.reserve_run("b")
    finish(journal, "b", "unknown")
    page = journal.source.read_page(old_head.cursor(0), head=old_head, limits=JournalReadLimits())
    assert [entry.record for entry in page.entries] == [first]
    head = journal.source.head(journal.stream)
    page = journal.source.read_page(head.cursor(0), head=head, limits=JournalReadLimits(max_positions=1))
    assert page.has_more
    page.verify(head.cursor(0), head, JournalReadLimits(max_positions=1))
    tiny = journal.source.read_page(head.cursor(0), head=head, limits=JournalReadLimits(max_bytes=1))
    assert tiny.problem.code == "journal.page_entry_too_large"


def test_slow_or_failed_observer_does_not_block_producer_or_change_outcome():
    entered, unblock = Event(), Event()
    def observer(record):
        entered.set()
        unblock.wait(3)
        raise RuntimeError("raw sensitive detail")
    journal = OrchestrationJournal("session", telemetry_sink=observer, observer_queue_size=1)
    journal.reserve_run("run")
    journal.emit("run.started", correlation())
    assert entered.wait(1)
    start = monotonic()
    for _ in range(30):
        journal.emit("task.ready", correlation(task_id="task"))
    terminal = finish(journal)
    assert monotonic() - start < 1
    assert terminal.outcome == "succeeded"
    assert journal.health_snapshot().observer_dropped > 0
    unblock.set()
    journal.close()
    assert journal.health_snapshot().observer_failed > 0


def test_invalid_fields_and_fictitious_completion_are_rejected():
    journal = OrchestrationJournal("session")
    with pytest.raises(TypeError):
        journal.emit("run.queued", correlation(), raw_parameters={"secret": "value"})
    with pytest.raises(ValueError, match="terminal_outcome_required"):
        journal.emit("run.finished", correlation())
    with pytest.raises(ValueError, match="terminal_reservation_required"):
        finish(journal)
    with pytest.raises(ValueError, match="count_invalid"):
        journal.emit("task.ready", correlation(task_id="task"), completed=-1)


def test_shared_work_identity_and_consumer_links_survive_codec():
    from stratbox.core.observability import ObjectRef
    record = record_from_orchestration_event(OrchestrationEvent(
        "shared_work.attached", "session", 1, TIME,
        correlation(shared_work_id="material"), references=(ObjectRef("run", "other", "consumer"),),
    ))
    restored = decode_record(encode_record(record))
    assert restored.correlation.shared_work_id == "material"
    assert restored.references[0].relation == "consumer"


def test_failed_terminal_publication_retains_same_obligation_for_retry(monkeypatch):
    journal = OrchestrationJournal("session", max_pending_runs=1)
    journal.reserve_run("run")
    append = journal.source.append_terminal
    attempts = []
    def fail_once(record):
        attempts.append(record)
        if len(attempts) == 1:
            raise OSError("transient publication failure")
        return append(record)
    monkeypatch.setattr(journal.source, "append_terminal", fail_once)
    record = finish(journal, outcome="succeeded")
    assert record.outcome == "succeeded"
    assert journal.health_snapshot().unpublished_transitions == 1
    assert journal.source.reserved == 1
    assert journal.flush_transitions() == 1
    assert attempts == [record, record]
    assert journal.health_snapshot().unpublished_transitions == 0
    assert journal.source.pending == 1
    assert journal.flush_transitions() == 0


def test_qualified_operation_effect_summary_uses_existing_capture_projection():
    from stratbox.core.execution import EffectReceipt
    journal = OrchestrationJournal("session")
    corr = correlation(task_id="write", attempt_id="attempt")
    definition = OperationDefinition("test.write", "write", int, int,
                                     possible_effects=frozenset({"test.write"}))
    def write(value, invocation):
        invocation.effect(EffectReceipt("test.write", "confirmed", effect_id="receipt", guarantee="verified"))
        return value
    result = run(definition, 4, write, context=ExecutionContext(correlation=corr, sink=journal))
    report = journal.capture_result(result, correlation=corr)
    assert report.accepted == report.produced == 1
    summary = journal.records[-1]
    assert summary.kind == "operation.result"
    assert summary.correlation == corr
    assert summary.payload["effects"][0]["effect_id"] == "receipt"
    finished = next(record for record in journal.records if record.kind == "operation.finished")
    assert summary.cause_record_ids == (finished.record_id,)


def test_forwarded_operation_events_share_bounded_queue_and_avoid_recursion():
    from stratbox.core.execution import ExecutionEvent
    entered, release = Event(), Event()
    class BlockedSink:
        def emit(self, event):
            entered.set()
            release.wait(3)
    journal = OrchestrationJournal("session", observer_queue_size=1)
    sink = journal.operation_sink(BlockedSink())
    assert journal.operation_sink(journal) is journal
    assert journal.operation_sink(sink) is sink
    event = ExecutionEvent(3, "operation.started", "invoke", "test", "method", 1,
                           TIME, correlation(task_id="task"))
    sink.emit(event)
    assert entered.wait(1)
    for _ in range(25):
        sink.emit(event)
    assert journal.health_snapshot().observer_dropped >= 24
    assert journal._queue.qsize() <= 1
    release.set()
    journal.close()
    assert journal._observer_bytes == 0
