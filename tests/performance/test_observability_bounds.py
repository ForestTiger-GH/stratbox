"""Bounded behavior depends on actual observed items, never maximum sequence."""
from datetime import datetime, timezone
import pytest

from stratbox.base.filestore import LocalFileStore
from stratbox.observability import (SequenceRange, find_gaps, merge_ranges,
                                    JournalRecord, RecordFilter, select_records,
                                    FileJournalReader, JournalNamespace, inspect_causes)

TIME = datetime(2026, 11, 15, tzinfo=timezone.utc)


def test_two_events_near_2_pow_53():
    upper = 2**53 - 1
    assert find_gaps((1, upper), expected_last=upper) == (SequenceRange(2,upper-1),)


def test_interval_generator_budget():
    def unbounded():
        while True:
            yield SequenceRange(1,1)
    with pytest.raises(ValueError):
        merge_ranges(unbounded())


def test_read_report_limits_infinite_paths(tmp_path):
    reader = FileJournalReader(LocalFileStore(str(tmp_path)), namespace=JournalNamespace("logs", "writer"),
                               max_segments=3)
    def many():
        for i in range(100_000_000):
            yield f"logs/writer/{i}.jsonl"
    report = reader.read_report(many())
    assert any(issue.code == "journal.segment_limit" for issue in report.issues)
    assert len(report.issues) <= 5


def test_causal_cycle_iterative():
    nodes = (
        JournalRecord("nodeA", "diagnostic", "test", TIME, {}, cause_record_ids=("nodeB",)),
        JournalRecord("nodeB", "diagnostic", "test", TIME, {}, cause_record_ids=("nodeA",)),
    )
    inspection = inspect_causes(nodes, "nodeA")
    assert len(inspection.roots) == 2 and not inspection.truncated
