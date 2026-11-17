from datetime import datetime, timezone

import pytest

from stratbox.system.base.filestore import LocalFileStore
from stratbox.system.execution import Correlation, ExecutionContext, OperationDefinition, run
from stratbox.system.observability import (
    DomainFact, FileJournalReader, FileJournalSource, FileJournalWriter, IndexedSegment,
    JournalDecodeError, JournalHead, JournalReadLimits, ObjectRef, RecordMemorySink,
    SegmentDescriptor, SnapshotJournalSource, StreamKey, build_operation_history,
    capture_operation_result, record_from_fact, record_from_result, summarize_operations,
)

TIME = datetime(2026, 11, 17, tzinfo=timezone.utc)
STREAM = StreamKey("public", "events", "one")


def _record(index):
    return record_from_fact(DomainFact(
        "fixture.domain", ObjectRef("fixture", "one"), f"fact-{index}", TIME,
        {"index": index}, observation_id=f"obs-{index}",
    ))


def test_file_index_uses_confirmed_extent_and_returns_prefix(tmp_path):
    store = LocalFileStore(tmp_path)
    writer = FileJournalWriter(store, "events", writer_id="owner")
    first = SegmentDescriptor.from_receipt(writer.write_batch((_record(1), _record(2))))
    second = SegmentDescriptor.from_receipt(writer.write_batch((_record(4),)))
    reader = FileJournalReader(store, namespace=writer.namespace)
    head = JournalHead(STREAM, "epoch", "index-v1", "owner", "resumable", 1, 4)
    source = FileJournalSource(reader, head, (IndexedSegment(1, first), IndexedSegment(4, second)))
    page = source.read_page(head.cursor(0), head=head, limits=JournalReadLimits())
    page.verify(head.cursor(0), head, JournalReadLimits())
    assert tuple(entry.offset for entry in page.entries) == (1, 2)
    assert page.problem.code == "journal.position_gap"
    assert (page.problem.first_offset, page.problem.last_offset) == (3, 3)
    assert page.storage_coverage == "incomplete"
    with (tmp_path / second.logical_locator).open("ab") as output:
        output.write(b" ")
    damaged = source.read_page(head.cursor(3), head=head, limits=JournalReadLimits())
    assert damaged.problem.code in {"journal.segment_identity_mismatch", "journal.segment_too_large"}
    assert not damaged.entries


def test_cursor_epoch_retention_and_pinned_snapshot(tmp_path):
    store = LocalFileStore(tmp_path)
    writer = FileJournalWriter(store, "events", writer_id="owner")
    segment = SegmentDescriptor.from_receipt(writer.write_batch((_record(5),)))
    reader = FileJournalReader(store, namespace=writer.namespace)
    head = JournalHead(STREAM, "epoch", "index-v1", "owner", "resumable", 5, 5)
    source = FileJournalSource(reader, head, (IndexedSegment(5, segment),))
    with pytest.raises(JournalDecodeError, match="journal.cursor_expired"):
        source.read_page(head.cursor(3), head=head, limits=JournalReadLimits())
    with pytest.raises(JournalDecodeError, match="journal.cursor_ahead"):
        source.read_page(head.cursor(6), head=head, limits=JournalReadLimits())
    page = source.read_page(head.cursor(4), head=head, limits=JournalReadLimits(max_positions=1))
    assert page.next_cursor.last_offset == 5
    assert page.storage_coverage == "complete"
    assert page.capture_coverage == "indeterminate"


def test_finished_summary_is_linked_and_snapshot_remains_volatile():
    sink = RecordMemorySink()
    definition = OperationDefinition("fixture.compute", 1, "arithmetic", int, int)
    context = ExecutionContext(sink=sink, correlation=Correlation("run"))
    result = run(definition, 4, lambda request, invocation: request + 2, context=context)
    capture_operation_result(result, sink)
    summary = sink.records[-1]
    finish = next(record for record in sink.records if record.kind == "operation.finished")
    assert summary.payload["data_version"] == 2
    assert summary.cause_record_ids == (finish.record_id,)
    assert summary.correlation == finish.correlation
    older_view = record_from_result(result, occurred_at_utc=TIME)
    history = build_operation_history((*sink.records, older_view), result.invocation_id)
    assert history.summary_record_id == summary.record_id
    assert summarize_operations((history, history)).total == 1
    source = SnapshotJournalSource(sink.finalize_generation(), STREAM, source_authority_id="owner", epoch_id="local")
    head = source.head(STREAM)
    page = source.read_page(head.cursor(0), head=head, limits=JournalReadLimits(max_positions=1))
    assert head.profile == "local_snapshot" and page.storage_coverage == "indeterminate"
    assert len(page.entries) == 1 and page.has_more
