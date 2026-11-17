"""Fault-injected offline file-journal integration; no background services."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.observability import (JournalRecord, FileJournalWriter, FileJournalReader,
                                    BufferedFileJournal, PersistencePolicy, RequiredJournalGate,
                                    JournalBarrierError)

TIME = datetime(2026, 11, 15, tzinfo=timezone.utc)


def rec(value):
    return JournalRecord(f"record_{value}", "diagnostic", "test.check", TIME, {"value": value})


def test_parallel_immutable_segment_has_single_creator(tmp_path):
    writer = FileJournalWriter(LocalFileStore(str(tmp_path)), "events", writer_id="writer")
    with ThreadPoolExecutor(max_workers=6) as pool:
        receipts = list(pool.map(lambda _: writer.write_batch((rec(1),)), range(18)))
    assert all(receipt.state == "confirmed" for receipt in receipts)
    assert sum(not receipt.already_present for receipt in receipts) == 1
    assert len({receipt.segment_id for receipt in receipts}) == 1


def test_missing_corrupt_and_cross_segment_conflict(tmp_path):
    store = LocalFileStore(str(tmp_path))
    writer = FileJournalWriter(store, "logs", writer_id="a")
    x = writer.write_batch((rec(1),))
    y = writer.write_batch((rec(2),))
    r = FileJournalReader(store, namespace=writer.namespace)
    ok = r.read_report((x.locator, y.locator))
    assert not ok.issues and len(ok.records) == 2 and not ok.complete
    (tmp_path / x.locator).write_bytes(b"{invalid\n")
    damaged = r.read_report((x.locator, y.locator))
    assert len(damaged.records) == 1 and damaged.issues[0].code == "journal.json_invalid"
    (tmp_path / y.locator).unlink()
    missing = r.read_report((y.locator,))
    assert missing.issues[0].code == "journal.segment_missing" and not missing.records


def test_required_barrier_under_lost_store_capability(tmp_path):
    class NoImmutable:
        def makedirs(self, path):
            pass
    writer = FileJournalWriter(NoImmutable(), "required", writer_id="a")
    called = []
    try:
        RequiredJournalGate(writer).execute_after_record(rec(1), lambda: called.append("executed"))
    except JournalBarrierError as error:
        assert error.receipt.state == "failed"
    else:
        assert False, "Barrier must reject store without immutable capability"
    assert not called


def test_buffer_close_and_reconcile_after_lost_ack(tmp_path):
    base = LocalFileStore(str(tmp_path))
    class UnknownCommit:
        def makedirs(self, path):
            return base.makedirs(path)
        def create_if_absent(self, path, data):
            base.create_if_absent(path, data)
            raise OSError("response lost")
        def open_read(self, path):
            return base.open_read(path)
    failing = FileJournalWriter(UnknownCommit(), "buffer", writer_id="a",
                                policy=PersistencePolicy(max_buffer_records=2))
    buffer = BufferedFileJournal(failing)
    assert buffer.append(rec(1)) is None
    result = buffer.append(rec(2))
    assert result.state == "unknown"
    assert len(buffer.pending) == 2
    assert buffer.close_status == "pending_unconfirmed"
    buffer.writer = FileJournalWriter(base, "buffer", writer_id="a",
                                     policy=PersistencePolicy(max_buffer_records=2))
    assert buffer.reconcile_pending().state == "confirmed"
    buffer.close()
    assert not buffer.pending and buffer.close_status == "closed_confirmed"
